# Hidroelectrica România - Integrare Home Assistant

Integrare pentru monitorizarea contului Hidroelectrica România.

## Instalare

### Prin HACS
1. Adaugă repository-ul ca repository personalizat: `https://github.com/usercristi/hidro`
2. Selectează categoria "Integration"
3. Instalează integrarea "Hidroelectrica România"

### Manual
1. Copiază folderul `custom_components/hidro` în directorul `custom_components` al Home Assistant
2. Repornește Home Assistant

## Configurare

1. Mergi la **Setări** → **Dispozitive și Servicii** → **Adaugă Integrare**
2. Caută "Hidroelectrica România"
3. Introdu username-ul și parola de la portalul Hidroelectrica
4. Selectează contul (UAN) pe care vrei să-l monitorizezi

## Senzori disponibili

- Date contract
- Sold factură
- Factură restantă
- Index energie (consum)
- Index producție (pentru prosumatori)
- Citire permisă (non-prosumatori)
- Arhivă consum lunar
- Arhivă citiri index
- Arhivă plăți
- Compensații ANRE (prosumatori)

## Suport

Pentru probleme sau sugestii, deschide un issue pe GitHub.