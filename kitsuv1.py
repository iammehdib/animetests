from easy_pil import Editor, Font, Canvas
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import requests
import io
import json

# Configuration (ajustée pour des étiquettes plus grandes et style AniList)
IMAGE_SIZE = (1200, 628)
TITLE_FONT_SIZE = 70
YEAR_FONT_SIZE = 30
FONT_PATH = "arial.ttf"
OPACITY = 0.8
OVERLAY_COLOR = (50, 50, 50)
BLUR_RADIUS = 5
LOGO_HEIGHT = 628
LOGO_MARGIN = 0
YEAR_SPACING = 5
MAX_CHARS_PER_LINE = 20

# Fonctions utilitaires (inchangées)
def get_anime_data(anime_id):
    url = f"https://kitsu.io/api/edge/anime/{anime_id}?include=categories,animeProductions.producer"
    headers = {"Accept": "application/vnd.api+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Erreur API Kitsu: {response.status_code}")

def download_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(io.BytesIO(response.content))
    else:
        raise Exception(f"Erreur téléchargement image: {response.status_code}")

def wrap_text_manual(text, max_chars):
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += word + " "
        else:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    
    return lines

def generate_banner(anime_id):
    # Récupérer les données de l'anime
    anime_data = get_anime_data(anime_id)
    
    # Récupérer les titres disponibles
    titles = anime_data["data"]["attributes"].get("titles", {})
    canonical_title = anime_data["data"]["attributes"]["canonicalTitle"]
    
    # Vérifier les titres anglophones (en ou en_us)
    en_title = titles.get("en") or titles.get("en_us") or None
    
    # Choisir le titre le plus court
    if en_title and len(en_title) < len(canonical_title):
        title = en_title
    else:
        title = canonical_title
    start_date = anime_data["data"]["attributes"].get("startDate", "N/A")
    episode_count = anime_data["data"]["attributes"].get("episodeCount", "N/A")  
    year = start_date.split("-")[0] if start_date != "N/A" else "N/A"
    cover_url = anime_data["data"]["attributes"].get("coverImage", {}).get("original") or \
                anime_data["data"]["attributes"]["posterImage"]["original"]
    logo_url = anime_data["data"]["attributes"]["posterImage"]["original"]

    # Récupérer les genres à partir de la section "included"
    genres = []
    if "included" in anime_data:
        for item in anime_data["included"]:
            if item["type"] == "categories":
                genre_title = item["attributes"].get("title")
                if genre_title:
                    genres.append(genre_title)
    
    # Limiter à 3 genres pour éviter un débordement
    genres = genres[:3]

    # Télécharger et préparer l'image de fond
    background = download_image(cover_url)
    background = background.convert("RGBA")

    # Redimensionner proportionnellement pour couvrir IMAGE_SIZE
    bg_width, bg_height = background.size
    target_width, target_height = IMAGE_SIZE
    ratio = max(target_width / bg_width, target_height / bg_height)
    new_width = int(bg_width * ratio)
    new_height = int(bg_height * ratio)
    background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Recadrer au centre pour obtenir exactement IMAGE_SIZE
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    background = background.crop((left, top, right, bottom))

    # Appliquer un flou
    background = background.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))

    # Créer un overlay gris foncé semi-transparent
    overlay = Image.new("RGBA", IMAGE_SIZE, (*OVERLAY_COLOR, int(255 * OPACITY)))
    background = Image.alpha_composite(background, overlay)

    # Télécharger et préparer le logo
    logo = download_image(logo_url)
    logo = logo.convert("RGBA")

    # Redimensionner le logo en respectant les proportions
    logo_ratio = logo.width / logo.height
    logo_width = int(LOGO_HEIGHT * logo_ratio)
    logo = logo.resize((logo_width, LOGO_HEIGHT), Image.Resampling.LANCZOS)

    # Créer une nouvelle image pour combiner fond et logo
    final_image = Image.new("RGBA", IMAGE_SIZE)
    final_image.paste(background, (0, 0))

    # Positionner le logo à droite avec une marge
    logo_x = IMAGE_SIZE[0] - logo_width - LOGO_MARGIN
    logo_y = (IMAGE_SIZE[1] - LOGO_HEIGHT) // 2
    final_image.paste(logo, (logo_x, logo_y), logo)

    # Convertir en RGB pour easy-pil
    final_image = final_image.convert("RGB")

    # Créer l'éditeur avec easy-pil
    editor = Editor(final_image)

    # Diviser le titre en lignes
    title_lines = wrap_text_manual(title, MAX_CHARS_PER_LINE)

    # Ajouter l'année
    font_year = Font.poppins(size=YEAR_FONT_SIZE, variant="bold")
    year_position = (60, 80)
    editor.text(
        year_position,
        year,
        font=font_year,
        color="white",
        align="left"
    )

    # Ajouter le titre ligne par ligne
    font_title = Font.poppins(size=TITLE_FONT_SIZE, variant="bold")
    title_y = 120
    line_spacing = TITLE_FONT_SIZE * 1.2
    for line in title_lines:
        editor.text(
            (60, title_y),
            line,
            font=font_title,
            color="white",
            align="left"
        )
        title_y += line_spacing
    
    # Ajouter le nombre d'épisodes sous l'année
    episode_text = f"{episode_count} ep." if episode_count != "N/A" else "N/A ep."
    editor.text(
        (60, title_y + 20),
        episode_text,
        font=font_year,
        color="white",
        align="left"
    )
    
    # Ajouter les genres en bas à gauche, alignés horizontalement
    genre_x = 60  # Marge à gauche
    genre_y = 534  # Position verticale
    font_genre = Font.poppins(size=30, variant="bold")

    for genre in genres:
        # Calculer la taille du texte
        text_bbox = font_genre.getbbox(genre)
        text_width = text_bbox[2] - text_bbox[0]

        # Définir les dimensions du rectangle
        rect_width = text_width + 2 * 12  # Padding de 12 de chaque côté
        rect_height = 40  # Hauteur fixe pour tous les rectangles

        # Dessiner le rectangle
        editor.rectangle(
            (genre_x, genre_y),
            width=rect_width,
            height=rect_height,
            fill=(200, 200, 200, 180),  # Gris semi-transparent
            radius=22  # Bords arrondis
        )

        # Calculer la position du texte pour le centrer
        text_x = genre_x + (rect_width - text_width) / 2
        text_y = genre_y + (rect_height / 2) - 12  # Centrer verticalement avec offset
        
        # Ajouter le texte
        editor.text(
            (text_x, text_y),
            genre,
            font=font_genre,
            color="white",  # Blanc
            align="left"
        )

        # Mettre à jour la position x pour le prochain genre
        genre_x += rect_width + 8  # Espacement de 8 entre rectangles

    # Sauvegarder l'image
    editor.save(f"media/banner_anime_{anime_id}.png")

# Exemple d'utilisation
if __name__ == "__main__":
    #anime_id = 21
    for anime_id in [21, 23]:
    #for anime_id in [23, 3250, 2519, 11209, 5646]:
        generate_banner(anime_id)
    print("Finish")