# main.py
import requests
import json
import urllib3
import os
from datetime import datetime

# === Desactivar advertencias de SSL (por certificado autofirmado) ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURACIÓN ===
REDMINE_URL = "https://gesproy.pagina.cu"
PROJECT_IDENTIFIER = "ps211lh010_001"
WIKI_PAGE_TITLE = "Referencias_academicas"
REDMINE_API_KEY = os.environ['REDMINE_API_KEY']  # Desde GitHub Secrets

# === BÚSQUEDA CIENTÍFICA ===
QUERY = "digital transformation environmental information system open data sustainability public sector"

# ================================
#       FUNCIONES
# ================================

def buscar_openalex(query, limit=3):
    """
    Busca artículos en OpenAlex (https://openalex.org)
    """
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "filter": "is_oa:true",  # Solo acceso abierto
        "per_page": limit,
        "sort": "cited_count_desc"
    }
    try:
        print("🔍 Buscando en OpenAlex...")
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", "Sin título"),
                    "authors": [author["author"]["display_name"] for author in item.get("authorships", [])[:4]],
                    "year": item.get("publication_year"),
                    "journal": item.get("primary_location", {}).get("source", {}).get("display_name", "Sin revista"),
                    "citations": item.get("cited_count", 0),
                    "abstract": item.get("abstract", "No disponible"),
                    "url": item.get("primary_location", {}).get("landing_page_url") or item.get("doi", "#")
                })
            print(f"✅ {len(results)} artículos encontrados en OpenAlex.")
            return results
        else:
            print(f"❌ Error OpenAlex {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error conexión OpenAlex: {str(e)}")
        return []

def buscar_doaj(query, limit=3):
    """
    Busca artículos en DOAJ (https://doaj.org)
    """
    url = "https://doaj.org/api/v2/search/articles"
    query_str = f"title:{query} OR abstract:{query}"
    params = {
        "q": query_str,
        "page": 1,
        "pageSize": limit
    }
    try:
        print("🔍 Buscando en DOAJ...")
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", [])[:limit]:
                bibjson = item.get("bibjson", {})
                link = next((l for l in item.get("links", []) if l.get("type") == "fulltext"), {})
                results.append({
                    "title": bibjson.get("title", "Sin título"),
                    "authors": [author.get("name", "Anónimo") for author in bibjson.get("author", [])[:4]],
                    "year": bibjson.get("year", "N/A"),
                    "journal": bibjson.get("journal", {}).get("title", "Revista desconocida"),
                    "citations": "N/A",
                    "abstract": bibjson.get("abstract", "No disponible"),
                    "url": link.get("url", "#")
                })
            print(f"✅ {len(results)} artículos encontrados en DOAJ.")
            return results
        else:
            print(f"❌ Error DOAJ {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error conexión DOAJ: {str(e)}")
        return []

def combinar_resultados(query, limit_openalex=3, limit_doaj=3):
    """
    Combina resultados de OpenAlex y DOAJ.
    """
    papers = []
    papers += buscar_openalex(query, limit_openalex)
    papers += buscar_doaj(query, limit_doaj)

    # Eliminar duplicados por título
    seen = set()
    unique_papers = []
    for paper in papers:
        title = paper["title"].lower()
        if title not in seen:
            seen.add(title)
            unique_papers.append(paper)

    return unique_papers

def formatear_papers_markdown(papers):
    """
    Formatea los resultados en Markdown.
    """
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    md = f"""# Referencias Académicas - Transformación Digital del SIA

> Actualizado el {hoy} (automático)

Artículos científicos relevantes para el Sistema de Información Ambiental de Cuba.

---

"""
    if not papers:
        md += "❌ No se encontraron artículos científicos recientes.\n"
        return md

    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "Sin título")
        url = paper.get("url", "#")
        year = paper.get("year", "N/A")
        citations = paper.get("citations", "N/A")
        journal = paper.get("journal", "Sin revista")
        abstract = (paper.get("abstract") or "No disponible")[:350] + "..."

        authors = ", ".join(paper.get("authors", ["Anónimo"]))
        if len(paper.get("authors", [])) > 4:
            authors += " et al."

        md += f"""
### {i}. {title}

- **Autores:** {authors}
- **Año:** {year} | **Revista:** {journal}
- **Citas:** {citations}
- **Resumen:** {abstract}
- [🔗 Ver artículo]({url})

---

"""
    return md

def actualizar_wiki_redmine(contenido):
    """
    Actualiza la página del wiki en Redmine.
    """
    url = f"{REDMINE_URL}/projects/{PROJECT_IDENTIFIER}/wiki/{WIKI_PAGE_TITLE}.json"
    headers = {
        "Content-Type": "application/json",
        "X-Redmine-API-Key": REDMINE_API_KEY
    }
    data = {
        "wiki_page": {
            "text": contenido.strip(),
            "comments": f"Actualización automática - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        }
    }
    try:
        response = requests.put(
            url,
            data=json.dumps(data),
            headers=headers,
            timeout=15,
            verify=False  # Necesario por certificado autofirmado
        )
        if response.status_code in [200, 201]:
            print("✅ Éxito: Página del wiki actualizada.")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error al conectar con Redmine: {str(e)}")
        return False

# === EJECUCIÓN PRINCIPAL ===
def main():
    print("🚀 Iniciando actualización de referencias científicas...\n")
    resultados = combinar_resultados(QUERY, limit_openalex=3, limit_doaj=3)

    if not resultados:
        print("❌ No se encontraron artículos en ninguna fuente.")
        return

    contenido = formatear_papers_markdown(resultados)
    print("📝 Enviando a Redmine...")
    if actualizar_wiki_redmine(contenido):
        print("🎉 ¡Éxito! Tu wiki está actualizado.")
    else:
        print("⚠️ Falló la actualización en Redmine.")

if __name__ == "__main__":
    main()
