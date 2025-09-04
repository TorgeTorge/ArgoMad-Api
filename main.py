import uvicorn
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

from fastapi import FastAPI, HTTPException, Body, Form, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse

from selenium import webdriver
from selenium.webdriver.common.by import By
# MODIFICA: Aggiunto l'import per Service
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Modelli Pydantic ---
class SearchQuery(BaseModel):
    status: Optional[str] = Field(default="IN_CORSO", description="Stato dell'interpello")
    codice_ministeriale: Optional[str] = Field(default=None, description="Codice ministeriale")
    tipo_posto: Optional[str] = Field(default=None, description="Classe di concorso")
    provincia: Optional[str] = Field(default=None, description="Sigla della provincia")

# --- Inizializzazione FastAPI ---
app = FastAPI(
    title="School API Wrapper",
    description="API per interrogare il portale Argo.",
    version="4.0.0-env-fix"
)

# --- Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Funzioni di Scraping ---

def scrape_argo_live(query: SearchQuery):
    """
    Esegue lo scraping in tempo reale dal portale Argo MAD Interpello usando Selenium con Firefox.
    """
    firefox_options = Options()
    firefox_options.add_argument("--headless")

    try:
        #    Esegui 'which geckodriver' nel terminale per trovare il percorso corretto.
        geckodriver_path = "/usr/local/bin/geckodriver" # <-- SOSTITUISCI CON IL TUO PERCORSO SE DIVERSO!

        # 2. Crea un oggetto Service con il percorso specificato.
        service = Service(executable_path=geckodriver_path)

        # 3. Inizializza il driver passando l'oggetto service.
        driver = webdriver.Firefox(service=service, options=firefox_options)

    except Exception as e
        print(f"Errore inizializzazione Selenium per Firefox: {e}")
        raise HTTPException(status_code=500, detail="Configurazione Selenium (geckodriver) non corretta sul server.")

    results = []
    try:
        url = "https://madinterpello.portaleargo.it/#!/"
        print("[DEBUG] Navigazione verso l'URL di Argo...")
        driver.get(url)

        wait = WebDriverWait(driver, 30)

        # --- LOGICA DI NAVIGAZIONE ---
        seleziona_op_xpath = "//button[contains(., 'Seleziona operazione')]"
        print("[DEBUG] Attesa del pulsante 'Seleziona operazione'...")
        wait.until(EC.element_to_be_clickable((By.XPATH, seleziona_op_xpath))).click()

        interpello_docente_xpath = "//div[contains(@class, 'v-list-item__title')][contains(text(), 'Interpello per Personale Docente')]"
        print("[DEBUG] Attesa della voce di menu 'Interpello per Personale Docente'...")
        wait.until(EC.element_to_be_clickable((By.XPATH, interpello_docente_xpath))).click()
        
        # --- FILTRO PROVINCIA (se specificata) ---
        if query.provincia:
            provincia_input_xpath = "//input[@placeholder='Cerca interpelli per Regione, Provincia...']"
            print("[DEBUG] Attesa del campo di input della provincia...")
            provincia_input = wait.until(EC.element_to_be_clickable((By.XPATH, provincia_input_xpath)))
            
            print(f"[DEBUG] Inserimento provincia: {query.provincia}")
            provincia_input.click()
            provincia_input.send_keys(query.provincia)

            provincia_minuscola = query.provincia.lower()
            option_xpath = f"//div[contains(@class, 'v-list-item__title') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{provincia_minuscola}')]"
            print("[DEBUG] Attesa dell'opzione provincia nel dropdown...")
            wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath))).click()

        # --- FILTRO CLASSE DI CONCORSO (se specificata) ---
        if query.tipo_posto:
            tipo_posto_input_xpath = "//span[contains(text(), 'Seleziona le tipologie di posto')]/following-sibling::div//input"
            print("[DEBUG] Attesa del campo di input della classe di concorso...")
            tipo_posto_input = wait.until(EC.element_to_be_clickable((By.XPATH, tipo_posto_input_xpath)))

            print(f"[DEBUG] Inserimento classe di concorso: {query.tipo_posto}")
            tipo_posto_input.click()
            tipo_posto_input.send_keys(query.tipo_posto)
            
            tipo_posto_minuscolo = query.tipo_posto.lower()
            tipo_posto_option_xpath = f"//div[contains(@class, 'v-list-item__title') and starts-with(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{tipo_posto_minuscolo}')]"
            print("[DEBUG] Attesa dell'opzione classe di concorso nel dropdown...")
            wait.until(EC.element_to_be_clickable((By.XPATH, tipo_posto_option_xpath))).click()

        # --- LOGICA DI CLICK TRAMITE JAVASCRIPT ---
        search_button_xpath = "//button[contains(., 'Ricerca')]"
        print("[DEBUG] Attesa del pulsante di ricerca...")
        search_button = wait.until(EC.element_to_be_clickable((By.XPATH, search_button_xpath)))
        
        print("[DEBUG] Esecuzione del click sul pulsante di ricerca tramite JavaScript...")
        driver.execute_script("arguments[0].click();", search_button)
        
        results_list_xpath = "//div[contains(@class, 'v-list-item-group')]"
        print("[DEBUG] Attesa della lista dei risultati...")
        time.sleep(2)
        wait.until(EC.visibility_of_element_located((By.XPATH, results_list_xpath)))
        
        print("[DEBUG] Estrazione dei risultati...")
        items = driver.find_elements(By.XPATH, "//div[contains(@class, 'v-list-item--link')]")
        
        for item in items:
            try:
                school_info = item.find_element(By.XPATH, ".//div[contains(@class, 'v-list-item__title')]").text
                address = item.find_element(By.XPATH, ".//div[contains(@class, 'v-list-item__subtitle')][1]").text
                position_info = item.find_element(By.XPATH, ".//div[contains(@class, 'v-list-item__subtitle')][2]").text
                deadline_info = item.find_element(By.XPATH, ".//div[contains(., 'Termine presentazione')]").text
                school_code, school_name = school_info.split("—", 1)
                results.append({
                    "school_code": school_code.strip(), "school_name": school_name.strip(),
                    "address": address.strip(), "position_code": position_info.split("—")[0].strip(),
                    "description": position_info.split("—")[1].strip().split(",")[0],
                    "deadline": deadline_info.replace("Termine presentazione", "").replace(":", "").strip()
                })
            except (NoSuchElementException, IndexError):
                continue
        print(f"[DEBUG] Trovati {len(results)} risultati.")

    except TimeoutException:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        screenshot_file = f"argo_timeout_error_{timestamp}.png"
        driver.save_screenshot(screenshot_file)
        print(f"[ERRORE] Timeout durante l'attesa di un elemento. Controlla lo screenshot: {screenshot_file}")
        return []
    except Exception as e:
        print(f"Errore durante lo scraping di Argo: {e}")
        raise HTTPException(status_code=500, detail=f"Errore imprevisto durante lo scraping di Argo: {e}")
    finally:
        print("[DEBUG] Chiusura del browser Selenium.")
        driver.quit()
        
    return results

async def interact_with_argo_api(query: SearchQuery):
    """Chiama la funzione di scraping live per Argo."""
    return scrape_argo_live(query)


# --- Endpoint API ---
@app.post("/api/search")
async def search_interpelli(query: SearchQuery = Body(...)):
    """Endpoint per la ricerca live su Argo."""
    try:
        results = await interact_with_argo_api(query)
        if not results:
            return {"message": "Nessun risultato da Argo.", "data": []}
        return {"message": f"Trovati {len(results)} risultati da Argo.", "data": results}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Errore durante l'elaborazione della richiesta: {str(e)}")

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    """Serve il file HTML dell'interfaccia utente."""
    return "index.html"

# --- Avvio Server ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
