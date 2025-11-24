/*
 cni_udp_sim.c
 CNI simulation with UDP I/O (single-file)
 - Listens for UDP text packets to update TARGET and INERTIAL inputs
 - Runs periodic simulation steps (dt)
 - Sends NAV/TRACK/COMM outputs via UDP to client (by default sends to the most recent sender)

 Compile:
   gcc -O2 -Wall -o cni_udp_sim cni_udp_sim.c -lm

 Run:
   ./cni_udp_sim  --listen-port 5005  --dt 1.0
   // optionally: --out-host 192.168.1.10 --out-port 6006

 Protocol (text CSV over UDP):
   TARGET,id,lat,lon,alt,vN,vE,vD,azimuth,iff
   INERTIAL,ego_lat,ego_lon,ego_alt,airspeed,groundspeed,ax,ay,az,wx,wy,wz,pitch,roll,yaw
   COMM_PKT,src,dst,tx_power_dbm,frequency_hz,timestamp_s,payload
 Outputs:
   NAV,t,lat,lon,alt,heading,groundspeed,airspeed,pitch,roll,yaw
   TRACK,t,id,est_lat,est_lon,est_alt,vN,vE,vD,snr,iff_classified
   COMM,t,src,dst,rx_snr,decoded_payload_or_status

 Notes:
  - Simple text protocol for easy testing. Not secure. For production use binary or structured protocols.
  - This program is single-threaded and uses select() for incoming UDP packets.
*/

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include <stdarg.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/select.h>

#define MAX_TARGETS 128
#define BUF_SIZE 2048
#define DEG2RAD (M_PI/180.0)
#define RAD2DEG (180.0/M_PI)

/* --- Data Structures (same as previous design) --- */

/* Input: Target */
typedef struct {
    int id;
    double lat_deg;
    double lon_deg;
    double alt_m;
    double vel_ned_mps[3]; /* N,E,D */
    double azimuth_deg;
    int iff_code;
    int valid; /* whether this slot is active */
} Target;

/* Shortwave packet input */
typedef struct {
    int source_id;
    int dest_id;
    double tx_power_dbm;
    double frequency_hz;
    double timestamp_s;
    char payload[256];
    int valid;
} ShortwavePacket;

typedef struct {
    int tacan_active;
    int ils_active;
    int adf_active;
} RadioSystemInputs;

/* Inertial/Atmos inputs */
typedef struct {
    double ego_lat_deg;
    double ego_lon_deg;
    double ego_alt_m;
    double airspeed_mps;
    double groundspeed_mps;
    double accel_mps2[3];
    double ang_rate_rps[3];
    double attitude_deg[3]; /* pitch, roll, yaw */
    int valid;
} InertialAtmosInputs;

/* Global inputs container */
typedef struct {
    Target targets[MAX_TARGETS];
    int target_count;
    ShortwavePacket sw_packet;
    RadioSystemInputs radio_inputs;
    InertialAtmosInputs nav_inputs;
    double sim_time_s;
    double dt_s;
} CNIInputs;

/* Outputs */
typedef struct {
    double lat_deg;
    double lon_deg;
    double alt_m;
    double heading_deg;
    double groundspeed_mps;
    double airspeed_mps;
    double attitude_deg[3];
    double timestamp_s;
} NavOutput;

typedef struct {
    int id;
    double est_lat_deg;
    double est_lon_deg;
    double est_alt_m;
    double est_v_ned[3];
    int iff_classified;
    double track_snr_db;
} TrackOutput;

typedef struct {
    int source_id;
    int dest_id;
    double rx_snr_db;
    char decoded_payload[256];
    double timestamp_s;
} CommOutput;

typedef struct {
    NavOutput nav;
    TrackOutput tracks[MAX_TARGETS];
    int track_count;
    CommOutput comm;
} CNIOutputs;

/* --- Helper functions --- */
static double normalize_heading(double hdg) {
    while (hdg < 0) hdg += 360.0;
    while (hdg >= 360.0) hdg -= 360.0;
    return hdg;
}

/* latitude/longitude offset by north/east meters (approx) */
static void latlon_offset(double lat_deg, double lon_deg,
                          double north_m, double east_m,
                          double *out_lat_deg, double *out_lon_deg) {
    const double R = 6378137.0;
    double dlat = north_m / R;
    double dlon = east_m / (R * cos(lat_deg * DEG2RAD));
    *out_lat_deg = lat_deg + dlat * RAD2DEG;
    *out_lon_deg = lon_deg + dlon * RAD2DEG;
}

/* estimate target simple */
static void estimate_target(const Target *t, double dt, TrackOutput *out) {
    out->id = t->id;
    double north = t->vel_ned_mps[0] * dt;
    double east = t->vel_ned_mps[1] * dt;
    double down = t->vel_ned_mps[2] * dt;
    double est_lat, est_lon;
    latlon_offset(t->lat_deg, t->lon_deg, north, east, &est_lat, &est_lon);
    out->est_lat_deg = est_lat;
    out->est_lon_deg = est_lon;
    out->est_alt_m = t->alt_m - down;
    out->est_v_ned[0] = t->vel_ned_mps[0];
    out->est_v_ned[1] = t->vel_ned_mps[1];
    out->est_v_ned[2] = t->vel_ned_mps[2];
    if (t->iff_code == 0) out->iff_classified = 0;
    else if (t->iff_code > 0) out->iff_classified = 1;
    else out->iff_classified = 2;
    double latdiff = (out->est_lat_deg - t->lat_deg) * DEG2RAD;
    double londiff = (out->est_lon_deg - t->lon_deg) * DEG2RAD;
    double approx_dist = sqrt(latdiff*latdiff + londiff*londiff) * 6378137.0;
    double snr = 30.0 - 20.0*log10(1.0 + approx_dist/1000.0);
    out->track_snr_db = snr;
}

/* process shortwave */
static void process_shortwave(const ShortwavePacket *pkt, const InertialAtmosInputs *nav,
                              CommOutput *out) {
    if (!pkt->valid) {
        out->source_id = -1;
        out->dest_id = -1;
        out->rx_snr_db = -9999.0;
        strcpy(out->decoded_payload, "[NO_PKT]");
        out->timestamp_s = 0;
        return;
    }
    out->source_id = pkt->source_id;
    out->dest_id = pkt->dest_id;
    out->timestamp_s = pkt->timestamp_s;
    /* placeholder pathloss: use tx - PL(d) */
    double dist_km = 100.0; /* placeholder */
    double rx_snr = pkt->tx_power_dbm - (20.0 * log10(dist_km + 1.0)) - 100.0;
    out->rx_snr_db = rx_snr;
    if (rx_snr > -10.0) {
        strncpy(out->decoded_payload, pkt->payload, sizeof(out->decoded_payload)-1);
        out->decoded_payload[sizeof(out->decoded_payload)-1] = '\0';
    } else {
        snprintf(out->decoded_payload, sizeof(out->decoded_payload), "[UNDECODABLE]");
    }
}

/* generate nav output */
static void generate_nav_output(const InertialAtmosInputs *navin, double sim_time, NavOutput *navout) {
    navout->lat_deg = navin->ego_lat_deg;
    navout->lon_deg = navin->ego_lon_deg;
    navout->alt_m = navin->ego_alt_m;
    navout->airspeed_mps = navin->airspeed_mps;
    navout->groundspeed_mps = navin->groundspeed_mps;
    navout->attitude_deg[0] = navin->attitude_deg[0];
    navout->attitude_deg[1] = navin->attitude_deg[1];
    navout->attitude_deg[2] = navin->attitude_deg[2];
    navout->heading_deg = normalize_heading(navin->attitude_deg[2]);
    navout->timestamp_s = sim_time;
}

/* main processing step */
static void cni_process_step(const CNIInputs *in, CNIOutputs *out) {
    generate_nav_output(&in->nav_inputs, in->sim_time_s, &out->nav);
    /* tracks */
    int tc = 0;
    for (int i = 0; i < MAX_TARGETS; ++i) {
        if (in->targets[i].valid) {
            estimate_target(&in->targets[i], in->dt_s, &out->tracks[tc]);
            tc++;
            if (tc >= MAX_TARGETS) break;
        }
    }
    out->track_count = tc;
    process_shortwave(&in->sw_packet, &in->nav_inputs, &out->comm);
}

/* --- Networking utilities --- */
static int create_udp_listener(int port) {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) { perror("socket"); return -1; }
    int on = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));
    struct sockaddr_in addr;
    memset(&addr,0,sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;
    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(sock);
        return -1;
    }
    return sock;
}

static ssize_t send_udp(int sock, const char *host, int port, const char *buf, size_t buflen) {
    struct sockaddr_in dest;
    memset(&dest,0,sizeof(dest));
    dest.sin_family = AF_INET;
    dest.sin_port = htons(port);
    if (inet_pton(AF_INET, host, &dest.sin_addr) <= 0) {
        return -1;
    }
    return sendto(sock, buf, buflen, 0, (struct sockaddr*)&dest, sizeof(dest));
}

/* --- Parsing incoming lines --- */
static void trim_newline(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n-1]=='\n' || s[n-1]=='\r')) { s[n-1]=0; n--; }
}

/* parse TARGET line */
static void handle_target_line(CNIInputs *in, const char *line) {
    /* format: TARGET,id,lat,lon,alt,vN,vE,vD,azimuth,iff */
    int id;
    double lat, lon, alt, vN, vE, vD, az;
    int iff;
    int ret = sscanf(line, "TARGET,%d,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%d",
                     &id, &lat, &lon, &alt, &vN, &vE, &vD, &az, &iff);
    if (ret >= 9) {
        /* find existing slot or empty slot */
        int slot = -1;
        for (int i=0;i<MAX_TARGETS;i++){
            if (in->targets[i].valid && in->targets[i].id == id) { slot = i; break; }
            if (slot==-1 && !in->targets[i].valid) slot = i;
        }
        if (slot >= 0) {
            Target *t = &in->targets[slot];
            t->id = id;
            t->lat_deg = lat;
            t->lon_deg = lon;
            t->alt_m = alt;
            t->vel_ned_mps[0] = vN;
            t->vel_ned_mps[1] = vE;
            t->vel_ned_mps[2] = vD;
            t->azimuth_deg = az;
            t->iff_code = iff;
            t->valid = 1;
            /* update count */
            int cnt=0; for (int i=0;i<MAX_TARGETS;i++) if (in->targets[i].valid) cnt++;
            in->target_count = cnt;
            fprintf(stderr,"[INFO] TARGET updated id=%d\n", id);
        } else {
            fprintf(stderr,"[WARN] No slot for new target id=%d\n", id);
        }
    } else {
        fprintf(stderr,"[WARN] BAD TARGET format: %s\n", line);
    }
}

/* parse INERTIAL line */
static void handle_inertial_line(CNIInputs *in, const char *line) {
    /* INERTIAL,ego_lat,ego_lon,ego_alt,airspeed,groundspeed,ax,ay,az,wx,wy,wz,pitch,roll,yaw */
    InertialAtmosInputs *n = &in->nav_inputs;
    int ret = sscanf(line, "INERTIAL,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf",
                     &n->ego_lat_deg, &n->ego_lon_deg, &n->ego_alt_m,
                     &n->airspeed_mps, &n->groundspeed_mps,
                     &n->accel_mps2[0], &n->accel_mps2[1], &n->accel_mps2[2],
                     &n->ang_rate_rps[0], &n->ang_rate_rps[1], &n->ang_rate_rps[2],
                     &n->attitude_deg[0], &n->attitude_deg[1], &n->attitude_deg[2]);
    if (ret >= 14) {
        n->valid = 1;
        fprintf(stderr,"[INFO] INERTIAL updated (lat=%.6f lon=%.6f)\n", n->ego_lat_deg, n->ego_lon_deg);
    } else {
        fprintf(stderr,"[WARN] BAD INERTIAL format: %s\n", line);
    }
}

/* parse COMM_PKT */
static void handle_comm_pkt_line(CNIInputs *in, const char *line) {
    /* COMM_PKT,src,dst,tx_power_dbm,frequency_hz,timestamp_s,payload */
    ShortwavePacket *p = &in->sw_packet;
    /* We'll parse first 6 comma-separated fields, then remaining as payload (no supporting commas inside payload here) */
    char tag[32];
    int src, dst;
    double tx, freq, tstamp;
    char payload[256] = {0};
    int ret = sscanf(line, "COMM_PKT,%d,%d,%lf,%lf,%lf,%255s",
                     &src, &dst, &tx, &freq, &tstamp, payload);
    if (ret >= 6) {
        p->source_id = src;
        p->dest_id = dst;
        p->tx_power_dbm = tx;
        p->frequency_hz = freq;
        p->timestamp_s = tstamp;
        strncpy(p->payload, payload, sizeof(p->payload)-1);
        p->valid = 1;
        fprintf(stderr,"[INFO] COMM_PKT updated src=%d dest=%d\n", src, dst);
    } else {
        fprintf(stderr,"[WARN] BAD COMM_PKT format: %s\n", line);
    }
}

/* dispatch line */
static void handle_incoming_line(CNIInputs *in, const char *line) {
    if (strncmp(line, "TARGET,", 7) == 0) handle_target_line(in, line);
    else if (strncmp(line, "INERTIAL,", 9) == 0) handle_inertial_line(in, line);
    else if (strncmp(line, "COMM_PKT,",9) == 0) handle_comm_pkt_line(in, line);
    else {
        fprintf(stderr,"[WARN] Unknown input: %s\n", line);
    }
}

/* --- Main program --- */
static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s [--listen-port N] [--out-host ip] [--out-port M] [--dt seconds]\n"
            "Defaults: listen-port=5005 out-host=(last sender) out-port=5006 dt=1.0\n", prog);
}

int main(int argc, char **argv) {
    int listen_port = 5005;
    char out_host[64] = {0};
    int out_port = 5006;
    double dt = 1.0;
    /* parse args */
    for (int i=1;i<argc;i++){
        if (strcmp(argv[i],"--listen-port")==0 && i+1<argc) { listen_port = atoi(argv[++i]); }
        else if (strcmp(argv[i],"--out-host")==0 && i+1<argc) { strncpy(out_host, argv[++i], sizeof(out_host)-1); }
        else if (strcmp(argv[i],"--out-port")==0 && i+1<argc) { out_port = atoi(argv[++i]); }
        else if (strcmp(argv[i],"--dt")==0 && i+1<argc) { dt = atof(argv[++i]); }
        else if (strcmp(argv[i],"--help")==0) { usage(argv[0]); return 0; }
    }

    int sock = create_udp_listener(listen_port);
    if (sock < 0) { fprintf(stderr,"Failed to create UDP listener\n"); return 1; }

    /* socket for sending out */
    int tx_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (tx_sock < 0) { perror("tx socket"); close(sock); return 1; }

    fprintf(stderr,"[INFO] Listening UDP port %d, dt=%.3f s, out_port=%d\n", listen_port, dt, out_port);

    /* initialize inputs */
    CNIInputs in;
    memset(&in,0,sizeof(in));
    in.dt_s = dt;
    in.sim_time_s = 0.0;
    /* no initial targets */

    CNIOutputs out;
    memset(&out,0,sizeof(out));

    /* for remembering last sender */
    struct sockaddr_in last_sender;
    socklen_t last_sender_len = 0;
    int have_last_sender = 0;

    /* set select timeout for dt */
    while (1) {
        /* compute next wake-up */
        struct timeval tv;
        tv.tv_sec = (int)floor(dt);
        tv.tv_usec = (int)((dt - floor(dt)) * 1e6);

        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(sock, &readfds);
        int nf = sock + 1;

        int rv = select(nf, &readfds, NULL, NULL, &tv);
        if (rv < 0) {
            if (errno == EINTR) continue;
            perror("select");
            break;
        }

        /* if data available, read all pending datagrams (non-blocking loop) */
        if (rv > 0 && FD_ISSET(sock, &readfds)) {
            /* read datagrams until empty */
            while (1) {
                char buf[BUF_SIZE];
                struct sockaddr_in sender;
                socklen_t slen = sizeof(sender);
                ssize_t n = recvfrom(sock, buf, sizeof(buf)-1, MSG_DONTWAIT, (struct sockaddr*)&sender, &slen);
                if (n < 0) {
                    if (errno == EAGAIN || errno == EWOULDBLOCK) break;
                    perror("recvfrom");
                    break;
                }
                buf[n] = '\0';
                trim_newline(buf);
                /* remember sender for reply if out_host unspecified */
                last_sender = sender;
                last_sender_len = slen;
                have_last_sender = 1;
                char sender_ip[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &sender.sin_addr, sender_ip, sizeof(sender_ip));
                fprintf(stderr,"[RX] %s:%d => %s\n", sender_ip, ntohs(sender.sin_port), buf);
                /* parse possibly multiple lines in buf */
                char *saveptr = NULL;
                char *line = strtok_r(buf, "\n", &saveptr);
                while (line) {
                    trim_newline(line);
                    handle_incoming_line(&in, line);
                    line = strtok_r(NULL, "\n", &saveptr);
                }
                /* continue to recv next datagram (non-blocking) */
            }
        }

        /* increment sim time and run a process step */
        in.sim_time_s += dt;
        cni_process_step(&in, &out);

        /* prepare outputs as text and send via UDP */
        char outbuf[2048];
        int len = 0;

        /* NAV */
        len = snprintf(outbuf, sizeof(outbuf),
                       "NAV,%.3f,%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n",
                       out.nav.timestamp_s, out.nav.lat_deg, out.nav.lon_deg, out.nav.alt_m,
                       out.nav.heading_deg, out.nav.groundspeed_mps, out.nav.airspeed_mps,
                       out.nav.attitude_deg[0], out.nav.attitude_deg[1], out.nav.attitude_deg[2]);
        if (len > 0) {
            if (strlen(out_host) > 0) {
                send_udp(tx_sock, out_host, out_port, outbuf, len);
            } else if (have_last_sender) {
                char ipstr[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &last_sender.sin_addr, ipstr, sizeof(ipstr));
                sendto(tx_sock, outbuf, len, 0, (struct sockaddr*)&last_sender, last_sender_len);
            }
        }

        /* TRACKS: send one per track */
        for (int i=0;i<out.track_count;i++){
            TrackOutput *t = &out.tracks[i];
            int l = snprintf(outbuf, sizeof(outbuf),
                             "TRACK,%.3f,%d,%.6f,%.6f,%.2f,%.2f,%.2f,%.2f,%.2f,%d\n",
                             out.nav.timestamp_s, t->id, t->est_lat_deg, t->est_lon_deg, t->est_alt_m,
                             t->est_v_ned[0], t->est_v_ned[1], t->est_v_ned[2],
                             t->track_snr_db, t->iff_classified);
            if (l>0) {
                if (strlen(out_host) > 0) send_udp(tx_sock, out_host, out_port, outbuf, l);
                else if (have_last_sender) sendto(tx_sock, outbuf, l, 0, (struct sockaddr*)&last_sender, last_sender_len);
            }
        }

        /* COMM */
        int l = snprintf(outbuf, sizeof(outbuf),
                         "COMM,%.3f,%d,%d,%.2f,%s\n",
                         out.comm.timestamp_s, out.comm.source_id, out.comm.dest_id,
                         out.comm.rx_snr_db, out.comm.decoded_payload);
        if (l>0) {
            if (strlen(out_host) > 0) send_udp(tx_sock, out_host, out_port, outbuf, l);
            else if (have_last_sender) sendto(tx_sock, outbuf, l, 0, (struct sockaddr*)&last_sender, last_sender_len);
        }

        /* loop continues */
    }

    close(sock);
    close(tx_sock);
    return 0;
}
