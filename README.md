# Parking Management System

This is a parking management system built with FastAPI and Python(FastAPI) MySQL, html css JavaScript. It provides complete functionalities including user registration and login, parking lot query, vehicle entry and exit, and more.

## Features

- **User Management**
  - User registration and login
  - Role-based access control (Admin / Regular User)
  - Session management and authentication

- **Parking Lot Management**
  - View all parking lots and their availability
  - View detailed parking lot info (location, capacity, pricing, etc.)
  - Admins can add and edit parking lot information

- **Parking Record Management**
  - Create parking records (vehicle entry)
  - End parking session (vehicle exit)
  - View personal parking history
  - Admins can view all parking records

- **Billing System**
  - Automatically calculates parking fees based on duration
  - Supports different rates for different parking lots

## Tech Stack

- **Backend**
  - FastAPI: A modern, high-performance Python web framework
  - SQLAlchemy: ORM (Object Relational Mapper)
  - Pydantic: Data validation and serialization
  - MySQL: Database
  - Uvicorn: ASGI server

- **Frontend**
  - HTML/CSS: Page structure and styling
  - JavaScript: Client-side interaction
  - Fetch API: Communicate with the backend

## Installation Guide

### Prerequisites

- Python 3.7+
- MySQL 5.7+


