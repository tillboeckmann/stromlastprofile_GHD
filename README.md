# Modellierung von Stromlastgängen der Querschnittstechnologien im Sektor Gewerbe, Handel, Dienstleistungen (GHD) zur Fortschreibung und Potenzialanalyse der Nachfrageflexibilisierung

Der vorliegende Python-Programmcode orientiert sich an vier Modulen nach Böckmann u.a. (2021) sowie Seim u.a. (2021):
1. Entwicklung branchen- und technologiespezifischer Lastprofile des deutschen GHD-Sektors im Jahr 2018
2. Fortschreibung der Lastprofile bis 2035 anhand von zwei literaturbasierten Energieverbrauchsszenarien
3. Quantifizierung zeitlich hochaufgelöster Nachfrageflexibilisierungspotenziale mithilfe eines Ansatzes nach Kleinhans (2014)
4. Regionalisierung der Nachfrageflexibilisierungspotenziale nach dem Forschungsprojekt [DemandRegio](https://github.com/DemandRegioTeam/disaggregator)
    
# Dateistruktur

Die Module werde aus zwei main-Dateien bedient, die im .ipynb- und .py-Format vorliegen. **main_modul1-2-3_stromlastgang_ghd** deckt Module 1-3 ab, **main_modul4_regionalisierung** entsprechend das Modul 4. Die Voraussetzung einer Ausführung des Regionalisierungsmodells ist eine vorherige Installation der [DemandRegio-Disaggregator-Bibliothek](https://github.com/DemandRegioTeam/disaggregator). Der Ordner **data_in/** beinhaltet alle Input-Dateien des Modells. Da bei Teilen des Inputs wie den Normen SIA 2024:2015, ISO 18523-1:2016 und DIN 18599-10:2018-09 eine Veröffentlichung nicht möglich ist, enthalten diese Tabellen lediglich Dummy-Daten. 

Die ersten beiden Modellierungsschritte des ersten Moduls der Arbeit sind mit Annahmen verbunden. Im ersten Schritt, der Entwicklung von Bottom-up-Lastprofilen, werden literaturbasierte Annahmen als Teil der Technologiedaten getroffen. Im zweiten Schritt werden die Lastprofile um strukturelle Annahmen ergänzt, die aus einem Vergleich mit den Branchenlastprofilen des Forschungsprojekts "DemandRegio" abgeleitet werden. Die genauen Annahmen werden von Böckmann u.a. (2021) beschrieben. Zur besseren Nachvollziehbarkeit der Modellierung ist jede Annahme mit einem Kürzel innerhalb dieses Programms versehen. **kuerzel_tabelle** fasst diese Anmerkungen zusammen und ist zusätzlich im Jupyter Notebook der entsprechenden main-Datei abgebildet. 

Die Ergebnisse des Modells umfassen als ersten Teil branchen- und technologiespezifische Stromlastgänge als Endergebnis des ersten Moduls im Ordner **data_out/results_lastgaenge/**. Diese beziehen sich auf das Jahr 2018 und umfassen folgende Branchen: büroähnliche Betriebe (WZ64-71), Handel (WZ47), Beherbergung (WZ55), Krankenhäuser (WZ86) und Schulen (WZ85) nach Destatis (2008). Der zweite Teil der an dieser Stelle veröffentlichten Ergebnisse besteht aus der Zusammenfassung regionalisierter Flexibilisierungspotenziale für das Basisszenario des Jahres 2035 und für das Status-Quo-Szenario des Jahres 2018 im Ordner **data_out/results_flexi/**. Die detaillierte Auflistung aller regionalisierten Lastgänge je Technologie sowie der Flexibilisierungspotenziale je Wirtschaftszweig mit einer Größe von 26 GB kann auf Nachfrage von den Autoren geteilt werden.

# Literatur

- **Böckmann, T. u.a. (2021).** *Ingenieurwissenschaftliche Modellierung branchen- und technologiespezifischer Lastprofile des Sektors Gewerbe, Handel, Dienstleistungen (GHD)*. Working Paper Energie und Ressourcen, Technische Universität Berlin. DOI: 10.5281/zenodo.4817980
- **DemandRegio - opendata.ffe.de**; URL: http://opendata.ffe.de/project/demandregio/ (besucht am 30.03.2021).
- **Gotzens, F. u. a. (2020).** *DemandRegio - Harmonisierung und Entwicklung von Verfahren zur regionalen und zeitlichen Auflösung von Energienachfragen.* Forschungsbericht. Berlin, Jülich, München. DOI: https://doi.org/10.34805/ffe-119-20
- **Kleinhans, D. (2014).** *Towards a systematic characterization of the potential of demand side management*. In: arXiv preprint arXiv:1401.4121. url: https://arxiv.org/pdf/1401.
4121.pdf (besucht am 21. 11. 2020).
- **Seim, S. u.a. (2021).** *Fortschreibung gewerblicher Lastprofile und Quantifizierung regionalisierter Lastflexibilisierungspotenziale*. Working Paper Energie und Ressourcen, Technische Universität Berlin. DOI: 10.5281/zenodo.4817512
- **Statistisches Bundesamt (Destatis) (2008).** *Klassifikation der Wirtschaftszweige.* url:https://www.destatis.de/static/DE/dokumente/klassifikation-wz-2008-3100100089004.pdf (besucht am 09. 11. 2020).

# Zitieren
Bitte zitieren Sie diese freie Software als:
- **Böckmann, T. und Seim, S. (2021).** *Modellierung von Stromlastgängen der Querschnittstechnologien im Sektor Gewerbe, Handel, Dienstleistungen (GHD) zur Fortschreibung und Potenzialanalyse der Nachfrageflexibilisierung*. DOI: 10.5281/zenodo.4906802.

# Lizenz

Die Python-Bibliothek wird als freie Software nach [GPLv3](http://www.gnu.org/licenses/gpl-3.0.en.html) lizenziert. Weitere Informationen unter [License](https://github.com/tillboeckmann/stromlastprofile_GHD/blob/main/LICENSE).
