![NADOO Connect Logo](https://github.com/NADOOITChristophBa/NADOO-Connect/assets/106314951/fa6ff6b4-bdb9-4621-ad04-8f6aa65f4aea)

# NADOO Connect

## GPT

<https://chat.openai.com/g/g-YbUmf9xif-nadoo-connect-senior-dev>

## About the Project

NADOO Connect is an innovative solution that enables customers to send automated messages to our company using email-based communication. This project serves as a bridge between customer PCs and our company's system, focusing on simplicity, security, and efficiency.

## How It Works

NADOO Connect uses email as the primary communication channel to securely and efficiently transfer data and commands. Customer PCs send encrypted messages, which are received and processed by our system.

### Workflow Diagram

```mermaid
sequenceDiagram
    participant KundePC as Customer PC
    participant KundenEmail as Email Server
    participant KollegenPC as Colleague PC

    KundePC->>KundenEmail: Send encrypted message
    KundenEmail->>KollegenPC: Forward message
    KollegenPC->>KollegenPC: Process message and respond if necessary
```

## Installation and Usage

(Detailed instructions for installation and usage of the software)

## License

This project is licensed under the MIT License. For more details, see the LICENSE file.

## Contributors

(List of contributors and their roles in the project)

For more information and support, please contact <support@nadooit.de>.

## Update 0.1.1

### What's New

- Improved asyncio event loop management in `sender_loop` to enhance performance and prevent unnecessary restarts.
- Enhanced concurrency control using `portalocker` for managing the sender loop.
- Added detailed debug print statements in the sender loop for better monitoring and troubleshooting.

### Fixes

- Addressed an issue where the sender loop was not terminating correctly after being idle.
- Resolved potential concurrency issues with multiple executions and sender loop restarts.

### Known Issues

- There are no known issues as of this update.
