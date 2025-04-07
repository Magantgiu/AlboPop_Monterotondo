import requests
import json
import datetime
import time
import random
from bs4 import BeautifulSoup
import pytz
import feedgenerator
import os
import re
from urllib.parse import urljoin
import logging

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Rimuovi FileHandler per evitare di scrivere file di log
    ]
)

# URL base dell'albo pretorio di Monterotondo
BASE_URL = "https://servizionline.hspromilaprod.hypersicapp.net/cmsmonterotondo/portale/albopretorio/albopretorioconsultazione.aspx?P=400"

def get_user_agent():
    """Restituisce un User-Agent casuale per evitare blocchi"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    return random.choice(user_agents)

def get_session():
    """Configura e restituisce una sessione HTTP"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    })
    return session

def get_viewstate_data(soup):
    """Estrae i dati di viewstate dalla pagina con gestione degli errori e logging migliorato"""
    try:
        # Crea un dizionario per immagazzinare tutti i campi hidden del form
        form_data = {}
        
        # Trova tutti gli input hidden nel form
        all_inputs = soup.find_all("input", {"type": "hidden"})
        if not all_inputs:
            logging.error("Nessun campo hidden trovato nella pagina")
            # Salva la pagina per debug
            with open("error_page_no_hidden_fields.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            return None
        
        # Logga tutti i campi trovati per debug
        logging.info(f"Trovati {len(all_inputs)} campi hidden")
        
        # Estrai tutti i campi hidden
        for input_field in all_inputs:
            name = input_field.get("name")
            value = input_field.get("value", "")
            if name:
                form_data[name] = value
                logging.debug(f"Campo hidden trovato: {name} (lunghezza valore: {len(value)})")
        
        # Verifica che ci siano almeno i campi essenziali
        required_fields = ["__VIEWSTATE", "__VIEWSTATEGENERATOR"]
        for field in required_fields:
            if field not in form_data:
                logging.error(f"Campo richiesto {field} non trovato")
                return None
        
        # Logga specificamente sulla presenza o assenza di EVENTVALIDATION
        if "__EVENTVALIDATION" in form_data:
            logging.info("Campo __EVENTVALIDATION trovato")
        else:
            logging.warning("Campo __EVENTVALIDATION non trovato, ma potrebbe non essere necessario")
            # In alcune implementazioni di ASP.NET, EVENTVALIDATION potrebbe essere optional
            # o gestito in modo diverso, quindi procediamo comunque
        
        return form_data
            
    except Exception as e:
        logging.error(f"Errore nell'estrazione dei dati ViewState: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def parse_table_data(soup):
    """Estrae i dati dalla tabella dell'albo pretorio"""
    items = []
    try:
        # Identifica la tabella principale
        table = soup.find("table", {"id": lambda x: x and 'dgRisultati' in x})
        if not table:
            logging.error("Tabella dei risultati non trovata")
            return items
            
        # Estrai le righe della tabella (escludi l'intestazione e il footer)
        rows = table.find_all("tr")[1:-1]  # Prima riga è intestazione, ultima potrebbe essere paginazione
        
        for row in rows:
            try:
                # Estrai le celle
                cells = row.find_all("td")
                if len(cells) < 4:  # Verifica che ci siano abbastanza celle
                    continue
                    
                # Estrai dati base
                num_doc = cells[0].text.strip() if cells[0] else ""
                oggetto = cells[1].text.strip() if cells[1] else "Documento senza titolo"
                data_pubbl = cells[2].text.strip() if cells[2] else ""
                data_scadenza = cells[3].text.strip() if cells[3] else ""
                
                # Crea entry
                item = {
                    "title": f"{num_doc} - {oggetto}",
                    "description": f"Numero: {num_doc}<br>Data pubblicazione: {data_pubbl}<br>Data scadenza: {data_scadenza}<br>",
                    "link": BASE_URL,
                    "guid": f"monterotondo-{num_doc}-{data_pubbl.replace('/', '')}" if data_pubbl else f"monterotondo-{num_doc}-{int(time.time())}",
                    "pubDate": parse_date(data_pubbl)
                }
                
                items.append(item)
                logging.info(f"Estratto documento: {num_doc}")
            except Exception as e:
                logging.error(f"Errore nell'elaborazione di una riga della tabella: {e}")
                
        return items
    except Exception as e:
        logging.error(f"Errore nell'elaborazione della tabella: {e}")
        return items

def parse_date(date_str):
    """Converte una stringa data nel formato italiano in un oggetto datetime"""
    try:
        if date_str:
            # Prova vari formati di data
            formats = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
            for fmt in formats:
                try:
                    data_obj = datetime.datetime.strptime(date_str, fmt)
                    # Converti in tempo locale italiano
                    tz = pytz.timezone('Europe/Rome')
                    return tz.localize(data_obj)
                except ValueError:
                    continue
        
        # Se non riesce a convertire, usa la data corrente
        tz = pytz.timezone('Europe/Rome')
        return tz.localize(datetime.datetime.now())
    except Exception:
        # In caso di qualsiasi errore, usa la data corrente
        tz = pytz.timezone('Europe/Rome')
        return tz.localize(datetime.datetime.now())

def navigate_to_next_page(session, soup, current_page):
    """Naviga alla pagina successiva"""
    try:
        logging.info(f"Tentativo di navigazione alla pagina {current_page + 1}...")
        
        # Ottieni i dati ViewState necessari per il postback
        viewstate_data = get_viewstate_data(soup)
        if not viewstate_data:
            logging.error("Impossibile ottenere i dati ViewState")
            return None
            
        # Trova il link alla pagina successiva usando la classe CSS fornita
        next_page_num = current_page + 1
        
        # Cerca il link alla pagina successiva usando specificamente la classe DG_PagerCellPageLink
        # e il testo corrispondente alla pagina successiva
        next_page_link = None
        
        # Metodo 1: Ricerca con CSS selector specifico
        pager_links = soup.select("a.DG_PagerCellPageLink")
        for link in pager_links:
            if link.text.strip() == str(next_page_num):
                next_page_link = link
                logging.info(f"Trovato link alla pagina {next_page_num} usando il selettore CSS")
                break
        
        # Metodo 2: Ricerca nella tabella di paginazione
        if not next_page_link:
            logging.info("Tentativo di trovare link nella tabella di paginazione...")
            pager_tables = soup.select("table.pagerstyle td table")
            for table in pager_tables:
                links = table.select("a")
                for link in links:
                    if link.text.strip() == str(next_page_num):
                        next_page_link = link
                        logging.info(f"Trovato link alla pagina {next_page_num} nella tabella di paginazione")
                        break
                if next_page_link:
                    break
        
        # Metodo 3: Cerca direttamente il controllo ASP.NET
        if not next_page_link:
            # Cerca il pattern esatto dal selettore fornito
            dgRisultati_id = None
            for tag in soup.find_all(id=lambda x: x and "dgRisultati" in x):
                dgRisultati_id = tag.get('id')
                break
                
            if dgRisultati_id:
                # Costruisci il pattern dell'ID in base alla struttura ASP.NET
                pager_id_base = dgRisultati_id.replace("dgRisultati", "")
                potential_pager_ids = [
                    f"{pager_id_base}dgRisultati_ctl23_ctl{str(next_page_num).zfill(2)}",
                    f"{pager_id_base}dgRisultati$ctl23$ctl{str(next_page_num).zfill(2)}",
                    f"{dgRisultati_id}_ctl23_ctl{str(next_page_num).zfill(2)}",
                    f"{dgRisultati_id}$ctl23$ctl{str(next_page_num).zfill(2)}"
                ]
                
                for pid in potential_pager_ids:
                    link = soup.find("a", {"id": pid})
                    if link:
                        next_page_link = link
                        logging.info(f"Trovato link alla pagina {next_page_num} con ID: {pid}")
                        break
        
        if not next_page_link:
            logging.error(f"Link alla pagina {next_page_num} non trovato")
            return None
            
        # Estrai le informazioni necessarie per il postback
        event_target = ""
        if next_page_link.get('id'):
            event_target = next_page_link.get('id')
        elif next_page_link.get('href') and "__doPostBack" in next_page_link.get('href'):
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", next_page_link.get('href'))
            if match:
                event_target = match.group(1)
        elif next_page_link.get('onclick') and "__doPostBack" in next_page_link.get('onclick'):
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", next_page_link.get('onclick'))
            if match:
                event_target = match.group(1)
                
        if not event_target:
            # Se ancora non funziona, cerca nella pagina i link che hanno testo uguale al numero della pagina
            # poi guarda a quali eventi sono associati
            all_scripts = soup.find_all("script")
            for script in all_scripts:
                script_text = script.string
                if script_text and "WebForm_DoPostBackWithOptions" in script_text:
                    logging.info("Trovato script con WebForm_DoPostBackWithOptions, analisi...")
                    script_lines = script_text.split('\n')
                    for line in script_lines:
                        if f"'{next_page_num}'" in line and "__doPostBack" in line:
                            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", line)
                            if match:
                                event_target = match.group(1)
                                logging.info(f"Trovato target evento da script: {event_target}")
                                break
            
        if not event_target:
            # Ultimo tentativo: ispeziona gli attributi del link
            logging.info("Ultima analisi del link di paginazione:")
            for attr_name, attr_value in next_page_link.attrs.items():
                logging.info(f"  {attr_name}: {attr_value}")
            
            # Se c'è un parent con id, potrebbe essere un controllo .NET
            parent = next_page_link.parent
            if parent and parent.get('id'):
                logging.info(f"ID del parent: {parent.get('id')}")
                # Prova a usare l'ID del parent come base per l'evento
                event_target = f"{parent.get('id')}${next_page_link.get('id', 'ctl01')}"
                
        # Usa direttamente l'ID dell'elemento come target se tutto il resto fallisce
        if not event_target and next_page_link.get('id'):
            event_target = next_page_link.get('id')
            
        if not event_target:
            logging.error("Impossibile determinare l'evento target per la navigazione")
            return None
            
        logging.info(f"Evento target per la navigazione: {event_target}")
        
        # Prepara i dati per il postback
        data = viewstate_data.copy()
        data.update({
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            # Mantieni gli altri campi del form se necessario
            "ctl00$ContentPlaceHolder1$txtNumeroAtto": "",
            "ctl00$ContentPlaceHolder1$txtOggetto": "",
            "ctl00$ContentPlaceHolder1$txtDataDa": "",
            "ctl00$ContentPlaceHolder1$txtDataA": "",
            "ctl00$ContentPlaceHolder1$ddlArea": "0",
            "ctl00$ContentPlaceHolder1$ddlTipo": "0"
        })
        
        # Tenta di determinare i nomi dei controlli corretti
        form_controls = soup.find_all("input") + soup.find_all("select")
        for control in form_controls:
            control_id = control.get('id', '')
            if control_id and (
                "NumeroAtto" in control_id or
                "Oggetto" in control_id or 
                "DataDa" in control_id or
                "DataA" in control_id or
                "Area" in control_id or
                "Tipo" in control_id
            ):
                control_name = control.get('name', '')
                if control_name:
                    data[control_name] = control.get('value', '')
                    logging.info(f"Aggiunto controllo del form: {control_name} = {control.get('value', '')}")
        
        # Salva i dati di post per debug
        dump_post_data(data, f"post_data_page_{next_page_num}.json")
        
        # Esegui il postback
        logging.info(f"Esecuzione postback per navigare alla pagina {next_page_num}...")
        
        response = session.post(BASE_URL, data=data)
        if response.status_code != 200:
            logging.error(f"Errore nella navigazione alla pagina {next_page_num}: status code {response.status_code}")
            return None
            
        # Salva la risposta per debugging
        # with open(f"response_page_{next_page_num}.html", "w", encoding="utf-8") as f:
          #  f.write(response.text)
            
        new_soup = BeautifulSoup(response.text, "html.parser")
        
        # Verifica che siamo effettivamente nella pagina successiva
        # Controlla se c'è un indicatore di pagina corrente
        current_page_indicators = new_soup.select("span.DG_PagerCurrentPageCell")
        if current_page_indicators:
            for indicator in current_page_indicators:
                if indicator.text.strip() == str(next_page_num):
                    logging.info(f"Navigazione alla pagina {next_page_num} confermata tramite indicatore")
                    return new_soup
        
        # Se non troviamo un indicatore esplicito, facciamo un controllo indiretto
        # Ad esempio, verificando che ci siano risultati nella tabella
        table = new_soup.find("table", {"id": lambda x: x and 'dgRisultati' in x})
        if table and table.find_all("tr")[1:-1]:  # Se ci sono righe di dati
            logging.info(f"Navigazione alla pagina {next_page_num} riuscita")
            return new_soup
        else:
            logging.warning(f"Incerto se la navigazione alla pagina {next_page_num} sia riuscita")
            return new_soup  # Restituiamo comunque il risultato per tentare di proseguire
            
    except Exception as e:
        logging.error(f"Errore nella navigazione alla pagina successiva: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def analyze_pagination(soup):
    """Analizza e registra informazioni sulla struttura di paginazione per debug"""
    logging.info("Analisi della struttura di paginazione...")
    
    # Cerca tutti gli elementi con classe DG_PagerCellPageLink
    pager_links = soup.select("a.DG_PagerCellPageLink")
    logging.info(f"Trovati {len(pager_links)} link di paginazione con classe DG_PagerCellPageLink:")
    
    for i, link in enumerate(pager_links):
        logging.info(f"  Link {i+1}:")
        logging.info(f"    Testo: '{link.text.strip()}'")
        logging.info(f"    ID: '{link.get('id', 'N/A')}'")
        logging.info(f"    Href: '{link.get('href', 'N/A')}'")
        logging.info(f"    Onclick: '{link.get('onclick', 'N/A')}'")
        logging.info(f"    Class: '{link.get('class', 'N/A')}'")
    
    # Cerca anche la tabella di paginazione specifica
    pager_tables = soup.select("tr.pagerstyle td table")
    logging.info(f"Trovate {len(pager_tables)} tabelle di paginazione:")
    
    for i, table in enumerate(pager_tables):
        logging.info(f"  Tabella {i+1}:")
        cells = table.select("td")
        logging.info(f"    Contiene {len(cells)} celle")
        for j, cell in enumerate(cells):
            links = cell.select("a")
            if links:
                logging.info(f"    Cella {j+1} contiene {len(links)} link:")
                for k, link in enumerate(links):
                    logging.info(f"      Link {k+1}: '{link.text.strip()}' (ID: {link.get('id', 'N/A')})")

def dump_post_data(data, output_file="post_data.json"):
    """Salva i dati di post per debugging"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logging.info(f"Dati POST salvati in {output_file}")

def scrape_albo_pretorio(num_pages=3):
    """Esegue lo scraping dell'albo pretorio per il numero di pagine specificato"""
    session = get_session()
    all_documents = []
    
    # Carica la prima pagina
    try:
        logging.info(f"Caricamento pagina iniziale: {BASE_URL}")
        response = session.get(BASE_URL)
        if response.status_code != 200:
            logging.error(f"Errore nel caricamento della pagina iniziale: status code {response.status_code}")
            return all_documents
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Analizza la struttura della paginazione
        analyze_pagination(soup)
        
        # Salva la pagina HTML per debug
        with open("page_initial.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
    except Exception as e:
        logging.error(f"Errore nel caricamento della pagina iniziale: {e}")
        return all_documents
    
    # Elabora ogni pagina
    for page in range(1, num_pages + 1):
        logging.info(f"Elaborazione pagina {page}...")
        
        # Estrai dati dalla tabella corrente
        documents = parse_table_data(soup)
        all_documents.extend(documents)
        
        logging.info(f"Trovati {len(documents)} documenti nella pagina {page}")
        
        # Salva la pagina HTML per debug
        with open(f"page_{page}.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        
        # Vai alla pagina successiva se non è l'ultima
        if page < num_pages:
            logging.info(f"Navigazione alla pagina {page + 1}...")
            new_soup = navigate_to_next_page(session, soup, page)
            if not new_soup:
                logging.error(f"Impossibile navigare alla pagina {page + 1}")
                break
                
            soup = new_soup
            
            # Pausa tra le pagine
            sleep_time = random.uniform(2.0, 3.5)
            logging.info(f"Pausa di {sleep_time:.2f} secondi prima di elaborare la pagina successiva")
            time.sleep(sleep_time)
    
    return all_documents

def generate_rss_feed(documents, output_path="albopop_monterotondo.xml"):
    """Genera un feed RSS dai documenti raccolti"""
    try:
        feed = feedgenerator.Rss201rev2Feed(
            title="AlboPOP Comune di Monterotondo",
            link="https://servizionline.hspromilaprod.hypersicapp.net/cmsmonterotondo/portale/albopretorio/albopretorioconsultazione.aspx?P=400",
            description="Feed RSS non ufficiale dell'Albo Pretorio del Comune di Monterotondo",
            language="it",
            # Usa un URL pubblico del tuo repository GitHub dove sarà pubblicato il feed
            feed_url="https://raw.githubusercontent.com/TUO_USERNAME/TUO_REPO/main/albopop_monterotondo.xml"
        )
        
        for doc in documents:
            feed.add_item(
                title=doc["title"],
                link=doc["link"],
                description=doc["description"],
                unique_id=doc["guid"],
                pubdate=doc["pubDate"]
            )
        
        with open(output_path, "w", encoding="utf-8") as f:
            feed.write(f, "utf-8")
            
        logging.info(f"Feed RSS generato correttamente in: {output_path}")
        
        return output_path
    except Exception as e:
        logging.error(f"Errore nella generazione del feed RSS: {e}")
        return None

def scrape_with_selenium():
    """Alternativa di scraping usando Selenium (da implementare se necessario)"""
    logging.info("Il metodo di scraping con Selenium non è ancora implementato")
    logging.info("Si consiglia di implementarlo se il metodo requests non funziona")
    
    # Qui andrebbe implementato il codice per Selenium
    # che userebbe il browser per navigare nel sito
    
    return []

if __name__ == "__main__":
    logging.info("Inizio scraping dell'Albo Pretorio di Monterotondo...")
    
    # Numero di pagine da elaborare
    NUM_PAGES = 5
    
    try:
        # Prima prova con requests
        documents = scrape_albo_pretorio(NUM_PAGES)
        
        # Se non ha funzionato, prova con Selenium
        if not documents:
            logging.info("Tentativo con requests fallito. Tentativo con Selenium...")
            documents = scrape_with_selenium()
        
        logging.info(f"Raccolti {len(documents)} documenti.")
        
        if documents:
            output_file = generate_rss_feed(documents)
            logging.info(f"Processo completato. Feed RSS salvato in: {output_file}")
        else:
            logging.error("Nessun documento raccolto. Impossibile generare il feed RSS.")
    except Exception as e:
        logging.error(f"Errore generale nell'esecuzione dello script: {e}")
        import traceback
        logging.error(traceback.format_exc())
