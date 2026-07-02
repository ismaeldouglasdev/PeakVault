<p align="center">
  <a href="README.md">🇧🇷 Português</a> &nbsp;|&nbsp; <strong>🇺🇸 English</strong>
</p>

# PeakVault

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/CustomTkinter-1F6FEB?style=flat-square&logo=python&logoColor=white" alt="CustomTkinter">
  <img src="https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/Matplotlib-11557C?style=flat-square&logo=python&logoColor=white" alt="Matplotlib">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT">
</p>

JSON file analysis and processing system with a modern GUI. Dynamic CRUD, data grouping, and graphical visualization — adaptable to any flat JSON list.

![1](assets/1-peakvault.png)

---

## Overview

PeakVault is a personal productivity tool for managing flat JSON lists. It provides an intuitive graphical interface to organize collections like anime, movies, games, or any structured dataset, with full CRUD support, dynamic grouping, and chart generation.

## Features

- **Full CRUD** — Add, edit, delete, and save items with automatic adaptation to the loaded JSON keys
- **Generic loading** — Opens any flat JSON list; form fields adjust automatically to the file's keys
- **Dynamic grouping** — Group data by any available key for segmented analysis
- **Chart visualization** — Matplotlib chart generation based on selected groupings
- **Search** — Search bar to filter items in the loaded list
- **Visual feedback** — Status bar with last action performed and error handling across all functions

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core language |
| CustomTkinter | Modern dark-blue GUI |
| Pandas | JSON data analysis and processing |
| Matplotlib | Chart generation |

## How to Use

1. Install dependencies:
   ```bash
   pip install customtkinter pandas matplotlib
   ```
2. Run the main script:
   ```bash
   python interface.py
   ```
3. In the interface, load a JSON list via the "Carregar lista" button
4. Use the buttons on the left for CRUD, grouping, or chart visualization

> Compatible with Windows 10, 11, and Linux.

## Project Structure

```
PeakVault/
├── interface.py                              # GUI (CustomTkinter)
├── logica.py                                 # Data processing logic
├── ranking_animes(sample_json_para_testar).json  # Sample JSON for testing
├── assets/                                   # Project screenshots
├── LICENSE                                   # MIT
└── README.md
```

## Screenshots

![2](assets/2-peakvault.png)

![3](assets/3-peakvault.png)

![4](assets/4-peakvault.png) ![5](assets/5-peakvault.png)

## Limitations

- Designed for flat JSON lists (no nested objects)
- Initially built for personal use tracking anime, movies, and game metrics

## License

Distributed under the **MIT** license. See [LICENSE](LICENSE) for more information.

---

Built by [Ismael Douglas](https://github.com/ismaeldouglasdev).
