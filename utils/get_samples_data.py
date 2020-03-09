import os
import json

import pyodbc


def get_SampleType():
    SampleTypes = []
    # Specifying the ODBC driver, server name, database, etc. directly
    cnxn = pyodbc.connect(os.environ.get('PDATA_DB'))
    cursor = cnxn.cursor()
    cursor.execute("SELECT sampleTypeId, name, nameAlts, nameChs, nameChsAlts, dataType, allowedDataRange, defaultRefRange, unit FROM [HMP3-Dev].dbo.T_SampleType;")

    for row in cursor.fetchall():
        st = {
            'sampleTypeId' : row[0],
            'name' : row[1],
            'nameAlts' : row[2],
            'nameChs' : row[3],
            'nameChsAlts': row[4],
            'dataType': row[5],
            'allowedDataRange': row[6],
            'defaultRefRange': row[7],
            'unit': row[8],
        }
        SampleTypes.append(st)
    return SampleTypes

# with open('st_new.json', 'w') as f:
#     json.dump(SampleTypes, f, ensure_ascii=False, indent=2)
