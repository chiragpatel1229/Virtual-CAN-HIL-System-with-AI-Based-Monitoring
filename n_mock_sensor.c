/*
 * Mock Sensor Node (STM32 Simulation)
 *
 * This program simulates a simple battery sensor running on an STM32-like device.
 * It sends voltage and temperature data over a TCP connection to a gateway,
 * behaving like a real embedded sensor in a Hardware-in-the-Loop setup.
 *
 * The goal of this mock sensor is to generate realistic battery behavior,
 * including normal operation, gradual degradation, increasing noise,
 * and occasional fault conditions, so that the rest of the system
 * can be tested and validated safely.
 *
 * This file is intentionally written in a clear and readable style
 * to help beginners understand how sensor simulation works.
 */


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h>
#include <stdint.h>

#define PORT 4000

int main() {
    int server_fd;
    int new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);

    unsigned char buffer[5];

    // These variables are used to simulate aging and degradation
    // I keep them global inside main so their values persist over time
    float noise_amplitude = 2.0f;
    long degradation_counter = 0;

    // ------------------------------------------------------------
    // 1. Setup TCP server
    // This simulates a real STM32 sensor talking to a gateway
    // ------------------------------------------------------------

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    // Allow reuse of the port if the program restarts
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        perror("setsockopt failed");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 3) < 0) {
        perror("Listen failed");
        exit(EXIT_FAILURE);
    }

    printf("========================================\n");
    printf("[MOCK SENSOR] Simulated STM32 started\n");
    printf("[MOCK SENSOR] Listening on TCP port %d\n", PORT);
    printf("========================================\n");
    printf("Waiting for Gateway connection...\n");

    new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
    if (new_socket < 0) {
        perror("Accept failed");
        exit(EXIT_FAILURE);
    }

    printf("[MOCK SENSOR] Gateway connected\n");
    printf("[MOCK SENSOR] Starting sensor data stream\n");

    // ------------------------------------------------------------
    // 2. Sensor simulation variables
    // ------------------------------------------------------------

    uint16_t voltage_mv = 3300;
    uint8_t temp_c = 45;

    long total_packets_sent = 0;

    srand(time(NULL));

    // ------------------------------------------------------------
    // 3. Main simulation loop
    // ------------------------------------------------------------

    while (1) {
        total_packets_sent++;
        degradation_counter++;

        // --------------------------------------------------------
        // Normal battery behavior
        // Simple sawtooth voltage pattern
        // This makes the data look realistic and non static
        // --------------------------------------------------------

        voltage_mv += 10;

        if (voltage_mv > 4000) {
            voltage_mv = 3000;
        }

        // --------------------------------------------------------
        // Gradual degradation model
        // Noise slowly increases over time
        // This simulates aging battery behavior
        // --------------------------------------------------------

        if (degradation_counter % 100 == 0) {
            noise_amplitude += 0.5f;
        }

        int noise = (rand() % (int)(noise_amplitude * 2)) - (int)noise_amplitude;
        voltage_mv += noise;

        // --------------------------------------------------------
        // Slow voltage sag after long operation
        // This represents capacity loss over time
        // --------------------------------------------------------

        if (degradation_counter > 600) {
            if (voltage_mv > 200) {
                voltage_mv -= 1;
            }
        }

        // --------------------------------------------------------
        // Hard fault injection
        // Only starts after AI has learned clean behavior
        // This simulates a sudden battery failure
        // --------------------------------------------------------

        if (total_packets_sent > 300) {
            int chance = (rand() % 100) + 1;

            if (chance <= 2) {
                voltage_mv = 100;
            }
        }

        // --------------------------------------------------------
        // Packet format
        // [0] Start byte 0xAA
        // [1] Voltage high byte
        // [2] Voltage low byte
        // [3] Temperature
        // [4] Checksum
        // --------------------------------------------------------

        buffer[0] = 0xAA;
        buffer[1] = (voltage_mv >> 8) & 0xFF;
        buffer[2] = voltage_mv & 0xFF;
        buffer[3] = temp_c;
        buffer[4] = (buffer[0] + buffer[1] + buffer[2] + buffer[3]) & 0xFF;

        send(new_socket, buffer, 5, 0);

        printf(
            "\r[TX] Seq:%ld | Voltage:%4dmV | Temp:%3dC | NoiseAmp:%.1f",
            total_packets_sent,
            voltage_mv,
            temp_c,
            noise_amplitude
        );

        printf(
            "\r[MOCK SENSOR TX] Seq:%ld | Volt:%4dmV | Temp:%3dC | NoiseAmp:%.1f",
            total_packets_sent,
            voltage_mv,
            temp_c,
            noise_amplitude
        );
        fflush(stdout);

        usleep(100000);
    }

    return 0;
}
