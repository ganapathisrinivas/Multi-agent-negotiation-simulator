# AI Driven Multi-Agent Negotiation Training & Simulation Platform

## About

This project is a real-estate negotiation simulation platform where multiple AI agents participate in a negotiation. The system uses Buyer and Seller agents that communicate with each other and make decisions based on their goals, personas, property details, and previous conversation.

## What I Implemented

### Orchestrator Agent

The Orchestrator Agent manages the complete negotiation flow. It controls whose turn it is, passes the conversation history between agents, maintains the current negotiation state, and keeps track of the negotiation rounds.

### Agent Reasoning Engine

An LLM-powered reasoning engine was implemented for the Buyer and Seller agents. Each agent receives its persona, goals, property information, and complete negotiation history to generate a context-aware response and offer.

### Counteroffer Evaluation

A counteroffer evaluation module was implemented to evaluate the offers received from the other agent. Based on the agent's goals and constraints, the agent can accept the offer, reject it, or generate a counteroffer.

### AI-to-AI Negotiation

The complete AI-to-AI negotiation loop was implemented and tested. The Buyer and Seller agents negotiate with each other through multiple rounds until they reach an agreement or the negotiation ends.

## Real Estate Scenarios

The system currently supports:

* Land / Plot
* Apartment / Flat
* Villa / Independent House

## Dataset

A real-estate dataset containing **14,528 properties** is used in the project.

The dataset contains information such as:

* Property Name
* Property Title
* Price
* Location
* Total Area
* Price per SQFT
* Description
* Baths
* Balcony

## Project Files

```text
agents/
├── orchestrator_agent.py
├── reasoning_engine.py
├── counteroffer_evaluator.py
└── __init__.py

dataset_real.csv
main.py
check_dataset.py
list_models.py
.gitignore
```

## Technologies

* Python
* LLM
* Multi-Agent System
* Real Estate Dataset
* GitHub

## Current Progress

The core AI negotiation components have been implemented and the end-to-end AI-to-AI negotiation flow has been tested across the available real-estate scenarios.
