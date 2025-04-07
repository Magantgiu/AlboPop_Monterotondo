# 1. Modificare il percorso di output del file RSS per renderlo relativo alla directory del progetto
def generate_rss_feed(documents, output_path="albopop_monterotondo.xml"):
    """Genera un feed RSS dai documenti raccolti"""
    try:
        feed = feedgenerator.Rss201rev2Feed(
            title="AlboPOP Comune di Monterotondo",
            link="https://servizionline.hspromilaprod.hypersicapp.net/cmsmonterotondo/portale/albopretorio/albopretorioconsultazione.aspx?P=400",
            description="Feed RSS non ufficiale dell'Albo Pretorio del Comune di Monterotondo",
            language="it",
            # Usa un URL pubblico del tuo repository GitHub dove sarà pubblicato il feed
            feed_url="https://raw.githubusercontent.com/Magantgiu/AlboPop_Monterotondo/main/albopop_monterotondo.xml"
        )
        
        # ... resto della funzione invariato ...

# 2. Modificare la configurazione del logging per ridurre la verbosità in GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Rimuovi FileHandler per evitare di scrivere file di log
    ]
)

# 3. Riduci o elimina il salvataggio di file temporanei di debug
# Esempio di modifica: condiziona il salvataggio delle pagine HTML
def navigate_to_next_page(session, soup, current_page):
    # ... codice esistente ...
    
    # Commenta o rimuovi questo codice in produzione
    # with open(f"response_page_{next_page_num}.html", "w", encoding="utf-8") as f:
    #     f.write(response.text)
    
    # ... resto della funzione invariato ...

# 4. Aggiorna il numero di pagine da scaricare in produzione
if __name__ == "__main__":
    # Imposta il numero di pagine adeguato per la produzione
    NUM_PAGES = 5  # o il valore che ritieni appropriato
