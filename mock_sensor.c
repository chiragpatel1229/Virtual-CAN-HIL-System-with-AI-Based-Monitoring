#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h>

#define PORT 4000

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    unsigned char buffer[5];

    // 1. Setup TCP Server (Simulating Wokwi)
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Force attach to port 4000
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    printf("========================================\n");
    printf("[MOCK SENSOR] Simulated STM32 Running...\n");
    printf("[MOCK SENSOR] Listening on Port %d\n", PORT);
    printf("========================================\n");
    printf("Waiting for Gateway to connect...\n");

    if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
        perror("accept");
        exit(EXIT_FAILURE);
    }

    printf("[MOCK SENSOR] Gateway Connected! Starting Data Stream.\n");

    // 2. Simulation Loop
    // Default Values
    uint16_t voltage_mv = 3300;
    uint8_t temp_c = 45;
    long total_packets_sent = 0; // Keep track of time
    int mode = 0; // 0=Normal, 1=Overheat, 2=LowVolt, 3=Random(Noise)

    while (1) {
        total_packets_sent++;
        // Simple User Input Simulation
        // We auto-fluctuate values slightly to make it look real
        
        // Random tiny fluctuation (-10 to +10 mV)
        // Normal Behavior (Sawtooth pattern)
        int noise = (rand() % 20) - 10;
        voltage_mv += 10; 
        if (voltage_mv > 4000) voltage_mv = 3000;
        
        // --- THE HACK ---
        // Only start glitching after 300 packets (30 seconds)
        // This gives the AI time to learn "Clean" data first.
        if (total_packets_sent > 300) {
            // Every 50th packet, trigger the fault
            if (total_packets_sent % 50 == 0) {
                voltage_mv = 100; // BATTERY FAILURE!
                printf(" [!!! GENERATING FAULT !!!] ");
            }
        }

        // Packetize: [0xAA] [VH] [VL] [T] [CS]
        buffer[0] = 0xAA;
        buffer[1] = (voltage_mv >> 8) & 0xFF;
        buffer[2] = voltage_mv & 0xFF;
        buffer[3] = temp_c;
        buffer[4] = (0xAA + buffer[1] + buffer[2] + buffer[3]) & 0xFF;

        send(new_socket, buffer, 5, 0);

        printf("\r[TX] Seq:%ld | Volt:%4dmV | Temp:%3dC", total_packets_sent, voltage_mv, temp_c);
        fflush(stdout);

        usleep(100000); // 10Hz 
    }
    return 0;
}