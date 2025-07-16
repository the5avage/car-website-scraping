# Car Alert

Project for datascience workflows at Berliner Hochschule für Technik.

A user can have multiple search queries for cars he is interested in. When a new interesting car is available at the website [autobid.de](https://autobid.de)
he is notified by email.

## Experimental setup

Information about vehicles was scraped from autobid.de. Questions in natural language

## Project structure

| directory | content |
|-----------|---------|
| data/ | Text data used for finetuning |
| src/01_data_acquisition/ | Scrape vehicle data and generate questions with openAI API |
| src/02_data_cleansing/ | Data cleaning |
| src/03_resource_testing/ | Some scripts for experimenting with models and token count |
| src/04_training_pipeline/ | Finetuning of RoBERTa and DeBERTa |
| src/05_car_alerts/ | Final application that runs at a specific time to check new vehicles and send notifications |
| src/06_evaluation/ | Zero shot evaluation of pretrained models and plots for comparison |


Further information is found in the notebooks and the [/src/05_car_alerts/README.md](/src/05_car_alerts/README.md).

## Requirements

There are 2 requirement files, one for CUDA 11 and one for CUDA 12. The finetuning scripts need CUDA12 while the others also work with the CUDA 11 requirements.