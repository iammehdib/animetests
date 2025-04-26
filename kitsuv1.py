from easy_pil import Editor, Font
from PIL import Image, ImageFilter
import requests
import io

# --- CONFIGURATION --- #

CONFIG = {
    "image_size": (1200, 628),
    "font_path": "arial.ttf",
    "title_font_size": 70,
    "year_font_size": 30,
    "description_font_size": 26,
    "genre_font_size": 30,
    "max_title_chars": 20,
    "max_description_chars": 300,
    "description_line_wrap": 50,
    "overlay_color": (0, 0, 0),
    "overlay_opacity": 0.9,
    "blur_radius": 5,
    "logo_margin": 0,
    "genre_max_per_line": 3,
    "genre_rect_height": 40,
    "genre_spacing": 8,
    "genre_radius": 22,
}

# --- OUTILS --- #

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

def wrap_text(text, max_chars):
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

# --- BANNIERE --- #

def generate_banner(anime_id):
    data = get_anime_data(anime_id)

    attributes = data["data"]["attributes"]
    titles = attributes.get("titles", {})
    canonical_title = attributes.get("canonicalTitle", "Unknown Title")
    en_title = titles.get("en") or titles.get("en_us")

    title = en_title if en_title and len(en_title) < len(canonical_title) else canonical_title
    start_date = attributes.get("startDate", "N/A")
    year = start_date.split("-")[0] if start_date != "N/A" else "N/A"
    episode_count = attributes.get("episodeCount", "N/A")
    description_raw = attributes.get("description", "Aucune description disponible.")
    cover_url = attributes.get("coverImage", {}).get("original") or attributes["posterImage"]["original"]
    logo_url = attributes["posterImage"]["original"]

    genres = [item["attributes"]["title"]
              for item in data.get("included", [])
              if item["type"] == "categories"]

    # --- Fond --- #

    background = download_image(cover_url).convert("RGBA")

    bg_w, bg_h = background.size
    target_w, target_h = CONFIG["image_size"]
    ratio = max(target_w / bg_w, target_h / bg_h)
    new_size = (int(bg_w * ratio), int(bg_h * ratio))
    background = background.resize(new_size, Image.Resampling.LANCZOS)

    left = (background.width - target_w) // 2
    top = (background.height - target_h) // 2
    background = background.crop((left, top, left + target_w, top + target_h))

    background = background.filter(ImageFilter.GaussianBlur(CONFIG["blur_radius"]))
    overlay = Image.new("RGBA", CONFIG["image_size"],
                        (*CONFIG["overlay_color"], int(255 * CONFIG["overlay_opacity"])))
    background = Image.alpha_composite(background, overlay)

    # --- Logo --- #

    logo = download_image(logo_url).convert("RGBA")
    logo_ratio = logo.width / logo.height
    logo_height = CONFIG["image_size"][1]
    logo_width = int(logo_ratio * logo_height)
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

    # --- Préparer l'image finale --- #

    final = Image.new("RGBA", CONFIG["image_size"])
    final.paste(background, (0, 0))

    logo_x = CONFIG["image_size"][0] - logo_width - CONFIG["logo_margin"]
    logo_y = (CONFIG["image_size"][1] - logo_height) // 2
    final.paste(logo, (logo_x, logo_y), logo)

    editor = Editor(final.convert("RGB"))

    # --- Texte --- #

    font_title = Font.poppins(size=CONFIG["title_font_size"], variant="bold")
    font_year = Font.poppins(size=CONFIG["year_font_size"], variant="bold")
    font_desc = Font.poppins(size=CONFIG["description_font_size"], variant="light")
    font_genre = Font.poppins(size=CONFIG["genre_font_size"], variant="light")

    # 1. TITRE
    title_y = 60
    for line in wrap_text(title, CONFIG["max_title_chars"]):
        editor.text((60, title_y), line, font=font_title, color="white", align="left")
        title_y += CONFIG["title_font_size"]

    # 2. ANNEE + EPISODES
    episode_text = f"{episode_count} EPISODE{'S' if episode_count != 'N/A' and episode_count > 1 else ''}" \
                   if episode_count != "N/A" else "N/A ep."
    title_y += 20
    editor.text((60, title_y), f"{year} - {episode_text}",
                font=font_year, color="white", align="left")
    title_y += CONFIG["year_font_size"] + 20

    # 3. DESCRIPTION
    short_desc = (description_raw[:CONFIG["max_description_chars"] - 3] + "...") \
        if len(description_raw) > CONFIG["max_description_chars"] else description_raw

    for line in wrap_text(short_desc, CONFIG["description_line_wrap"]):
        editor.text((60, title_y), line, font=font_desc,
                    color=(255, 255, 255, 180), align="left")
        title_y += CONFIG["description_font_size"] + 6

    # 4. GENRES
    title_y += 10

    def draw_genres(genres_list, start_x, start_y):
        lines = [genres_list[i:i + CONFIG["genre_max_per_line"]]
                 for i in range(0, len(genres_list), CONFIG["genre_max_per_line"])]
        for line_idx, line in enumerate(lines):
            x = start_x
            y = start_y + line_idx * (CONFIG["genre_rect_height"] + 12)
            for genre in line:
                text_w = font_genre.getbbox(genre)[2]
                rect_w = text_w + 24
                editor.rectangle(
                    (x, y),
                    width=rect_w,
                    height=CONFIG["genre_rect_height"],
                    fill=(255, 111, 97, 180),
                    radius=CONFIG["genre_radius"]
                )
                text_x = x + (rect_w - text_w) / 2
                text_y = y + (CONFIG["genre_rect_height"] - CONFIG["genre_font_size"]) / 2
                editor.text((text_x, text_y), genre, font=font_genre, color="white", align="left")
                x += rect_w + CONFIG["genre_spacing"]

    draw_genres(genres[:6], 60, title_y)

    # --- Sauvegarde --- #

    editor.save(f"media/banner_anime_{anime_id}.png")

# --- EXECUTION --- #

if __name__ == "__main__":
    anime_ids = [23, 3250, 2519, 11209, 5646]
    for anime_id in anime_ids:
        generate_banner(anime_id)
        print("Generate anime media " + str(anime_id))
    print("Generate finished !")
