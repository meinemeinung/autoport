autoport
=====

Simple Python application to monitor your investment and trading performance using yahoo-finance APIs.

All you need is to list all of your transactions and all corporate actions that is related to your stock holding to excel, run the update.py and you can now monitor how your investment portfolio perform historically!

## Usage
### Create virtual environment
```bash
python -m venv autoport-env
```

### Install requirements
```bash
autoport-env\Scripts\activate
pip install -r requirements.txt
```

### 

### Run
```bash
python src\update.py [LAST_UPDATE_DATE] [PATH_TO_EXCEL_SOUCE_FILE] --config [PATH_TO_CONFIG] --target [TARGET_DIRECTORY]
```

Example
```bash
python src\update.py 20240430 file/example.xlsx --config ./config/config.ini --target result/
```