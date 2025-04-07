import os
import shutil
import datetime

def archive_feed():
    """Archivia il feed RSS con timestamp"""
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    source_file = "albopop_monterotondo.xml"
    
    # Crea directory archive se non esiste
    archive_dir = "archive"
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
    
    # Copia il file nella directory di archivio con timestamp
    archive_file = f"{archive_dir}/albopop_monterotondo_{current_time}.xml"
    if os.path.exists(source_file):
        shutil.copy2(source_file, archive_file)
        print(f"Feed archiviato come {archive_file}")
    else:
        print(f"File {source_file} non trovato, nessun archivio creato")

if __name__ == "__main__":
    archive_feed()
