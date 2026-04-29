## Problem Statement: AI-Powered Restaurant Recommendation System (Zomato Use Case)

Build an AI-powered restaurant recommendation service inspired by Zomato. The system should suggest restaurants intelligently based on user preferences by combining structured restaurant data with a Large Language Model (LLM).

## Objective

Design and implement an application that:

- Accepts user preferences such as location, budget, cuisine, and minimum rating
- Uses a real-world restaurant dataset
- Leverages an LLM to generate personalized, human-like recommendations
- Presents clear, useful, and actionable results to the user

## System Workflow

### 1) Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face: [zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Extract key fields such as restaurant name, location, cuisine, cost, and rating

### 2) User Input

Collect the following preferences from the user:

- Location (for example, Delhi or Bangalore)
- Budget range (low, medium, high)
- Preferred cuisine (for example, Italian or Chinese)
- Minimum acceptable rating
- Additional preferences (for example, family-friendly or quick service)

### 3) Integration Layer

- Filter and prepare restaurant records based on user input
- Convert the filtered data into a structured prompt for the LLM
- Design the prompt so the LLM can reason effectively and rank options accurately

### 4) Recommendation Engine

Use the LLM to:

- Rank the best-matching restaurants
- Explain why each recommendation fits the user’s preferences
- Optionally provide a brief comparison among the top choices

### 5) Output Presentation

Display top recommendations in a clean and readable format, including:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation
