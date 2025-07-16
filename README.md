# Car Alert

Project for datascience workflows at Berliner Hochschule für Technik.

A user can have multiple search queries for cars he is interested in. When a new interesting car is available at the website [autobid.de](https://autobid.de)
he is notified by email.

## Experimental setup

Information about vehicles was scraped from autobid.de. For each car 5 positive and 5 negative questions where generated with GPT-4 (openAI API).

DeBERTa and RoBERTa models are then finetuned as Crossencoders for binary classification.
Additionally the performance of a 5 fold crossvalidation ensemble was evaluated.

Also pretrained crossencoders from the sentence_transformer library had been used as a baseline for comparison.

Finetuning achieved good performance for both models. DeBERTa achieved slightly better performance which is expected since it is a bigger and newer model.

An ensemble of 5 models trained with 5 fold crossvalidation did yield very minor improvements over a single model.

## Challenges

Especially challenging was to generate good labeled questions for finetuning. Generating labeled questions by hand was considered not feasible in the given timeframe.  
Different approaches to automatically generate the questions had been tried.  
For example we tried to generate the questions with an autogregressive LLM on the cluster. The results had been not good enough.  
Finally we used the openAI API to generate questions for 600 vehicles (6000 different questions).  
We used GPT-4 for the highest quality (questions with GPT-3.5-turbo or GPT-4-turbo had been to bad when manually inspecting the results).

## Rerun experiments

To rerun the experiments one needs to execute the notebooks in the order indicated by the prefixes.  
First one needs to scrape data and generate questions with the chatgpt api. (This can be skipped since the text data is in the data/ directory).  
Then data 

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