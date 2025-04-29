#include <Servo.h>

const int numServos = 3;  // Number of servos in use
Servo servos[numServos];   // Array of servo objects

const int potPins[numServos] = {A0, A1, A2};  // Assign a unique pin to each servo
bool potControl[numServos] = {true, true, true};  // Default: Potentiometer control for all servos
const int servoPins[numServos] = {2, 3, 4};    // Define servo pins

void setup() {
    Serial.begin(115200);
    for (int i = 0; i < numServos; i++) {  // itterates through number of servos
        //potControl[i].append
        servos[i].attach(servoPins[i]);  // Attach each servo to its pin
    }
}

void loop() {
    if (Serial.available() > 0) {  
        String message = Serial.readStringUntil('\n');  // Read full command
        processCommand(message);  // Process command
    }

    for (int i = 0; i < numServos; i++) {  
        if (potControl[i]) {  
            int sensorValue = analogRead(potPins[i]); // Read from the correct pot
            int angle = map(sensorValue, 0, 1023, 0, 180);           
            // **Send data in format: "potAddress:value"**
            Serial.print(getPinLabel(potPins[i]));
            Serial.print(":");
            Serial.println(sensorValue);  

            servos[i].write(angle);  // Move only the corresponding servo
        }
    }
    
    delay(100);  // Prevent spam
}

String getPinLabel(int pin) { // otherwise the ie A0, 
    switch (pin) {
        case A0: return "A0";
        case A1: return "A1";
        case A2: return "A2";
        case A3: return "A3";
        default: return String(pin);  // If unknown, return the number
    }
}

void processCommand(String command) {
    command.trim();  // Remove any whitespace

    if (command.length() == 0) return;  // Ignore empty commands

    // servo command (format: "servo_id:intruction")
    int separatorIndex = command.indexOf(':'); //find where the : is in the message
    if (separatorIndex == -1) return;  // if it isnt found, Invalid format, ignore

    int servoID = command.substring(0, separatorIndex).toInt(); // seperate ID
    String instruction = command.substring(separatorIndex + 1); // seperate instruction

    // Try using the instruction as an number (angle command)
    bool isNumber = true;
    for (int i = 0; i < instruction.length(); i++) {
        if (!isDigit(instruction[i])) {  // If any non-digit found, it's not a number
            isNumber = false;
            break;
        }
    }

    if (isNumber) {  
        int inst = instruction.toInt();  // Convert to integer
        if (servoID >= 1 && servoID <= numServos && inst >= 0 && inst <= 180) {
            int servoIndex = servoID - 1;  // Convert to index
            if (!potControl[servoIndex]) {  // Only move if in Python control mode
                servos[servoIndex].write(inst); // Move the servo
            }
        }
    } 
    else {  
        // Process mode switch command (True/False)
        if (instruction == "True") {
            potControl[servoID - 1] = true;
            Serial.print("Servo "); Serial.print(servoID); Serial.println(" in Potentiometer mode.");
        } 
        else if (instruction == "False") {
            potControl[servoID - 1] = false;
            Serial.print("Servo "); Serial.print(servoID); Serial.println(" in Python mode.");
        }
    }
}
