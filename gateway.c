/*
 * Gateway Node (Beginner Friendly Version)
 *
 * This program acts as a simple ECU gateway between a mock sensor
 * and a virtual CAN bus.
 *
 * It receives raw sensor data over TCP, performs basic safety checks,
 * packs the data into a CAN like frame, and forwards it over UDP
 * so that other tools (like the AI monitor) can listen.
 *
 * The gateway owns all safety logic. The AI is only allowed to observe.
 * This separation is intentional and important for safety systems.
 */


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <stdint.h>
#include <time.h>

#define SENSOR_IP   "127.0.0.1"
#define SENSOR_PORT 4000      // TCP connection to mock sensor

#define UDP_IP      "127.0.0.1"
#define UDP_PORT    5000      // Virtual CAN bus for AI listener

// Simple status codes used inside the CAN frame
#define STATUS_OK             0x00
#define STATUS_WARN_LOW_VOLT  0x01
#define STATUS_CRIT_TEMP      0x02

// Fake CAN frame structure
// This is not real CAN, but shaped similarly for learning purposes
typedef struct __attribute__((packed)) {
    uint32_t can_id;
    uint8_t  dlc;
    uint8_t  data[8];
} fake_can_frame_t;

int main() {
    int sock_tcp;
    int sock_udp;

    struct sockaddr_in sensor_addr;
    struct sockaddr_in udp_addr;

    fake_can_frame_t frame;

    // UART style packet from the sensor
    // [0xAA] [V_H] [V_L] [TEMP] [CHECKSUM]
    unsigned char buffer[5];

    printf("========================================\n");
    printf("[GATEWAY] Starting ECU Gateway\n");
    printf("[GATEWAY] Mode: Mock Sensor -> Virtual CAN\n");
    printf("========================================\n");

    // ------------------------------------------------------------
    // 1. Setup UDP socket (Virtual CAN Bus)
    // ------------------------------------------------------------

    sock_udp = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock_udp < 0) {
        perror("[Gateway] UDP socket creation failed");
        return 1;
    }

    memset(&udp_addr, 0, sizeof(udp_addr));
    udp_addr.sin_family = AF_INET;
    udp_addr.sin_port = htons(UDP_PORT);
    inet_pton(AF_INET, UDP_IP, &udp_addr.sin_addr);

    printf("[GATEWAY] Virtual CAN Bus ready on UDP %d\n", UDP_PORT);

    // ------------------------------------------------------------
    // 2. Setup TCP connection to mock sensor
    // ------------------------------------------------------------

    sock_tcp = socket(AF_INET, SOCK_STREAM, 0);
    if (sock_tcp < 0) {
        perror("[Gateway] TCP socket creation failed");
        return 1;
    }

    memset(&sensor_addr, 0, sizeof(sensor_addr));
    sensor_addr.sin_family = AF_INET;
    sensor_addr.sin_port = htons(SENSOR_PORT);
    inet_pton(AF_INET, SENSOR_IP, &sensor_addr.sin_addr);

    printf("[GATEWAY] Connecting to Mock Sensor on TCP %d...\n", SENSOR_PORT);

    // Retry until sensor becomes available
    while (connect(sock_tcp, (struct sockaddr *)&sensor_addr, sizeof(sensor_addr)) < 0) {
        printf("[GATEWAY] Waiting for Mock Sensor (is it running?)\n");
        sleep(2);
    }

    printf("[GATEWAY] Connected to Mock Sensor\n");
    printf("[GATEWAY] Starting data bridge\n");

    // ------------------------------------------------------------
    // 3. Main gateway loop
    // ------------------------------------------------------------

    while (1) {
        int bytes_read = 0;

        // Read exactly one full sensor packet (5 bytes)
        while (bytes_read < 5) {
            int result = recv(sock_tcp, buffer + bytes_read, 5 - bytes_read, 0);

            if (result <= 0) {
                printf("[GATEWAY] Sensor disconnected\n");
                close(sock_tcp);
                close(sock_udp);
                return 1;
            }

            bytes_read += result;
        }

        // --------------------------------------------------------
        // Basic packet validation
        // --------------------------------------------------------

        if (buffer[0] != 0xAA) {
            printf("[GATEWAY] Warning: Sync byte error (0x%02X)\n", buffer[0]);
            continue;
        }

        unsigned char volt_hi = buffer[1];
        unsigned char volt_lo = buffer[2];
        unsigned char temp    = buffer[3];
        unsigned char rx_cs   = buffer[4];

        unsigned char calc_cs = (0xAA + volt_hi + volt_lo + temp) & 0xFF;

        if (calc_cs != rx_cs) {
            printf("[GATEWAY] Warning: Checksum mismatch\n");
            continue;
        }

        uint16_t voltage_mv = (volt_hi << 8) | volt_lo;

        // --------------------------------------------------------
        // Safety logic
        // This is intentionally simple and deterministic
        // --------------------------------------------------------

        uint8_t status = STATUS_OK;

        if (temp > 60) {
            status = STATUS_CRIT_TEMP;
        } else if (voltage_mv < 3100) {
            status = STATUS_WARN_LOW_VOLT;
        }

        // --------------------------------------------------------
        // Prepare fake CAN frame
        // --------------------------------------------------------

        frame.can_id = 0x100;
        frame.dlc = 8;

        frame.data[0] = volt_hi;
        frame.data[1] = volt_lo;
        frame.data[2] = temp;
        frame.data[3] = status;

        // Remaining bytes are unused for now
        memset(&frame.data[4], 0, 4);

        // --------------------------------------------------------
        // Send frame on virtual CAN bus (UDP)
        // --------------------------------------------------------

        sendto(
            sock_udp,
            &frame,
            sizeof(frame),
            0,
            (struct sockaddr *)&udp_addr,
            sizeof(udp_addr)
        );
        

        printf(
            "\r[GATEWAY RX->TX] Volt:%4dmV | Temp:%3dC | Status:0x%02X",
            voltage_mv,
            temp,
            status
        );
        fflush(stdout);
        // Uncomment for debugging
        /*
        printf(
            "[GATEWAY TX] Volt:%4dmV | Temp:%3dC | Status:0x%02X\n",
            voltage_mv,
            temp,
            status
        );
        */
    }

    return 0;
}