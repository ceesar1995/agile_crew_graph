# AgileCrew

Dissertation project for the MSc in Artificial Intelligence at the University of Bath.

## Description

System based on LLM agents taking Agile Roles collaborate together for creating User Stories, Acceptance Criteria and Development Tasks for a given feature description and a project context.

## Installation and running

1. Clone the repository
2. Need to have Python at least 3.8 installed
3. Install the requirements
```bash
pip install -r requirements.txt
```
4. Prepare an .env file (must be placed inside /src folder) with the following variables:
```
AZURE_OPENAI_ENDPOINT
OPENAI_API_VERSION
````
These values are obtained from your azure cloud environment.
In case you also have different LLM models, you have to update them in the corresponding config yaml file inside src/config folder.
The config file used is referenced inside the src/Config.py file.
5. In case you can use the bluesheperd library, uncomment in the requirements.txt.
6. Run the streamlit app
```bash
streamlit run src/strealit_app.py
```
6. In case you can use the bluesheperd library.
```bash
streamlit run src/strealit_app_prototype.py
```