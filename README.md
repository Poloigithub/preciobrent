# Precio del barril de Brent

Seguimiento automático del precio del petróleo Brent en dólares (USD) usando datos de **Yahoo Finance**.

El script descarga el historial de precios, lo guarda en un CSV y genera un gráfico de evolución. Cada día laborable a las 7:00 (hora española), un workflow de GitHub Actions añade el precio del día y regenera la imagen automáticamente.

---

## Archivos

| Archivo | Descripción |
|---|---|
| `brent_price.py` | Script principal: descarga datos, actualiza el CSV y genera el gráfico |
| `brent_prices.csv` | Histórico de precios (fecha + precio en USD) |
| `brent_chart.png` | Gráfico de evolución generado automáticamente |
| `requirements.txt` | Dependencias Python necesarias |
| `.github/workflows/update_brent.yml` | Workflow de GitHub Actions para la actualización diaria |

---

## Uso

### 1. Instalación

```bash
pip install -r requirements.txt
```

### 2. Descarga inicial del histórico

Descarga todos los precios desde 2019 (configurable), guarda el CSV y genera el gráfico:

```bash
python brent_price.py init
```

Para elegir otra fecha de inicio:

```bash
python brent_price.py init --start 2015-01-01
```

### 3. Actualización manual

Añade el precio del día al CSV y regenera el gráfico:

```bash
python brent_price.py update
```

---

## Automatización con GitHub Actions

El workflow `.github/workflows/update_brent.yml` se ejecuta automáticamente de lunes a viernes a las 06:00 UTC (≈ 07:00 hora española en invierno):

1. Si el CSV no existe, lanza `init` para descargar todo el histórico.
2. Si el CSV ya existe, lanza `update` para añadir el precio del día.
3. Hace commit y push de `brent_prices.csv` y `brent_chart.png` al repositorio.

También se puede lanzar manualmente desde **Actions → Run workflow**.

> Para que el workflow pueda hacer push, asegúrate de que en **Settings → Actions → General** está activado **Read and write permissions**.

---

## Fuente de datos

- Precios: [Yahoo Finance](https://finance.yahoo.com) — ticker `BZ=F` (Brent Crude Oil Futures)
- Gráfico: [@poloi.bsky.social](https://bsky.app/profile/poloi.bsky.social)
