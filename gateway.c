#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <stdint.h>

#define SENSOR_IP "127.0.0.1"
#define SENSOR_PORT 4000  // Connected to mock_sensor.c
#define UDP_IP "127.0.0.1"
#define UDP_PORT 5000     // Virtual Bus for Python AI

// Status Codes
#define STATUS_OK 0x00
#define STATUS_WARN_LOW_VOLT 0x01
#define STATUS_CRIT_TEMP 0x02

// Structure that looks exactly like a CAN frame
typedef struct __attribute__((packed)) {
    uint32_t can_id;
    uint8_t dlc;
    uint8_t data[8];
} fake_can_frame_t;

int main() {
    int sock_tcp, sock_udp;
    struct sockaddr_in server_addr, udp_addr;
    fake_can_frame_t frame;
    
    // Buffer for UART packet: [HEAD, VOLT_H, VOLT_L, TEMP, CS]
    unsigned char buffer[5]; 

    printf("========================================\n");
    printf("[Gateway] System Launching...\n");
    printf("[Gateway] Mode: Plan C (Mock Sensor -> UDP)\n");
    printf("========================================\n");

    // ------------------------------------------------
    // 1. Setup UDP (The Virtual Bus)
    // ------------------------------------------------
    if ((sock_udp = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("[Error] UDP Socket creation failed");
        return 1;
    }

    memset(&udp_addr, 0, sizeof(udp_addr));
    udp_addr.sin_family = AF_INET;
    udp_addr.sin_port = htons(UDP_PORT);
    inet_pton(AF_INET, UDP_IP, &udp_addr.sin_addr);

    printf("[Gateway] Virtual CAN Bus active on UDP Port %d\n", UDP_PORT);

    // ------------------------------------------------
    // 2. Setup TCP Connection to Mock Sensor
    // ------------------------------------------------
    if ((sock_tcp = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("[Error] TCP Socket creation failed");
        return 1;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SENSOR_PORT);
    inet_pton(AF_INET, SENSOR_IP, &server_addr.sin_addr);

    printf("[Gateway] Connecting to Mock Sensor (TCP %d)...\n", SENSOR_PORT);
    
    // Retry loop
    while (connect(sock_tcp, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        printf("[Gateway] Waiting for Mock Sensor... (Is it running?)\n");
        sleep(2);
    }
    printf("[Gateway] Connected to Mock Sensor! Starting Bridge.\n");

    // ------------------------------------------------
    // 3. Main Loop
    // ------------------------------------------------
    while (1) {
        int bytes_read = 0;
        // Read exactly 5 bytes (blocking)
        while(bytes_read < 5) {
            int result = recv(sock_tcp, buffer + bytes_read, 5 - bytes_read, 0);
            if (result <= 0) {
                printf("[Gateway] Sensor disconnected.\n");
                close(sock_tcp);
                close(sock_udp);
                return 1;
            }
            bytes_read += result;
        }

        // --- Parsing ---
        if (buffer[0] != 0xAA) {
            printf("[Warn] Sync byte error. Got 0x%02X\n", buffer[0]);
            continue; 
        }

        unsigned char volt_hi = buffer[1];
        unsigned char volt_lo = buffer[2];
        unsigned char temp = buffer[3];
        unsigned char received_cs = buffer[4];

        unsigned char calculated_cs = (0xAA + volt_hi + volt_lo + temp) & 0xFF;

        if (calculated_cs != received_cs) {
            printf("[Warn] Checksum mismatch!\n");
            continue; 
        }

        uint16_t voltage_mv = (volt_hi << 8) | volt_lo;

        // --- Safety Logic ---
        uint8_t status = STATUS_OK;
        if (temp > 60) status = STATUS_CRIT_TEMP;
        else if (voltage_mv < 3100) status = STATUS_WARN_LOW_VOLT;

        // --- Prepare Fake CAN Frame ---
        frame.can_id = 0x100;
        frame.dlc = 8;
        frame.data[0] = volt_hi;
        frame.data[1] = volt_lo;
        frame.data[2] = temp;
        frame.data[3] = status;
        memset(&frame.data[4], 0, 4);

        // --- Send UDP Packet ---
        sendto(sock_udp, &frame, sizeof(frame), 0, 
               (struct sockaddr*)&udp_addr, sizeof(udp_addr));

        printf("[TX UDP] Volt:%4dmV | Temp:%3dC | Status:0x%02X\n", voltage_mv, temp, status);
    }
    return 0;
}