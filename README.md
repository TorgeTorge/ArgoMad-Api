Semplice progetto per fornire un'API "ponte" costruita con FastAPI per automatizzare la ricerca di interpelli


⚙️ Installazione e Configurazione

Segui questi passaggi per configurare l'ambiente ed eseguire il server in locale.
1. Prerequisiti

Assicurati di avere installato quanto segue:

    Python 3.8+ e pip
    fastapi
    bs4
    uvicorn
    pydantic
    requests

2. Configurazione del Progetto

    Clona il repository:

    Crea un ambiente virtuale (consigliato):

    python3 -m venv venv
    source venv/bin/activate

    (Su Windows, usa venv\Scripts\activate)

    Installa le dipendenze:

    pip install -r requirements.txt(prima o poi creo il file)

    Configura il percorso di Geckodriver 

3. Avvio del Server

Una volta completata la configurazione, avvia il server con Uvicorn:

uvicorn main:app --reload

Il server sarà accessibile all'indirizzo http://127.0.0.1:8000.
📖 Uso dell'API
Endpoint:
1. Ricerca Interpelli Argo

    URL: /api/search

    Metodo: POST

    Corpo della Richiesta (JSON):

    {
      "provincia": "xxxxx, xxxx",
      "tipo_posto": "ADEE - xxxxx" 
    }

    Risposta di Esempio:

    {
      "message": "Trovati 2 risultati da Argo.",
      "data": [
        {
          "school_code": "xxxxx",
          "school_name": "Istituto Comprensivo - \"xxxxxx\"",
          "address": "xxxxxx — xxxxx",
          "position_code": "ADEE",
          "description": "xxxxxx",
          "deadline": "xxxxxx"
        }
      ]
    }


🏡 Integrazione con Home Assistant


Aggiungi quanto segue al tuo file configuration.yaml:

rest:
  - resource: "http://<IP_DEL_SERVER>:8000/api/search"
    method: POST
    payload: '{ "provincia": "xxxx, xxxxx", "tipo_posto": "ADEE - xxxx" }'
    headers:
      Content-Type: "application/json"
    scan_interval: 3600 # Controlla ogni ora
    sensor:
      - name: "Interpelli Argo"
        unique_id: "interpelli_argo_sensor"
        value_template: "{{ value_json.data | count }}"
        json_attributes:
          - "data"
