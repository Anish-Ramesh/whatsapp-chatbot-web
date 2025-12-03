# Whatsapp-Chatbot

A feature-rich WhatsApp chatbot for grocery shopping, order management, and customer support, built with Flask and Python.

## Overview

This project implements a WhatsApp chatbot that allows users to interact with a grocery store via WhatsApp messages. Users can browse products, manage their cart, place and track orders, view order history, manage their account, and get support—all through a conversational interface.

## Features
- Product catalog browsing and search
- Add/remove items to/from cart
- Place, track, and cancel orders
- View order history and credit
- Multi-language support
- Address management
- Admin alerts and seller management
- Rate limiting and user context management
- Integration with MySQL database
- Modular, testable codebase

## How It Works
- The backend is built with Flask, exposing endpoints to receive and process WhatsApp webhook events.
- Incoming messages are parsed and routed to appropriate handlers based on user intent (e.g., catalog, cart, order, help).
- User and order data are stored in a MySQL database.
- The bot supports both text and button-based interactions, providing a rich conversational experience.
- Admin and seller features allow for alerting and management via the same chat interface.
- Environment variables are managed with python-dotenv.

## Uniqueness
- Designed for end-to-end grocery shopping on WhatsApp, including catalog, cart, and order management.
- Supports both customer and admin/seller workflows in a single bot.
- Modular architecture for easy extension and testing.
- Includes rate limiting, language, and address management for a robust user experience.
- Test suite included for core logic and handlers.

## Installation

Install all required dependencies using pip:

```sh
pip install -r requirements.txt
```

This will install all necessary packages for running and testing the project.

## Usage

1. Set up your `.env` file with the required environment variables (see `.env.example` if available).
2. Start your MySQL database and ensure the schema matches `updated_schema_v2.sql`.
3. Run the Flask app:
   ```sh
   python app.py
   ```
4. Configure your WhatsApp webhook to point to your server's endpoint.

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License.