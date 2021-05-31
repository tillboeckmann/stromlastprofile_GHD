
"""
Dieser Programmcode orientiert sich an drei Modulen nach Böckmann u.a. (2021) sowie Seim u.a. (2021):
    1. Entwicklung branchen- und technologiespezifischer Lastprofile des deutschen GHD-Sektors im Jahr 2018
    2. Fortschreibung der Lastprofile bis 2035 anhand von zwei literaturbasierten Energieverbrauchsszenarien
    3. Quantifizierung zeitlich hochaufgelöster Nachfrageflexibilisierungspotenziale mithilfe eines Ansatzes nach Kleinhans, (2014)

Das Programm verfügt über zwei Hauptmethoden (Lastgangsynthese und Szenario-Nachfrageflexi). Die erste Hauptmethode entspricht je nach gewählten Verhaltensparametern einem Modellschritt des ersten Moduls. Die zweite Hauptmethode führt Module zwei und drei aus. 


Das Programm verfügt über zwei Hauptmethoden (Lastgangsynthese und Szenario-Nachfrageflexi). 
Die erste Hauptmethode entspricht je nach gewählten Verhaltensparametern einem Modellschritt 
des ersten Moduls. Die zweite Hauptmethode führt Module zwei und drei aus. 

Die ersten beiden Modellierungsschritte des ersten Moduls der Arbeit sind mit Annahmen verbunden. 
Im ersten Schritt, der Entwicklung von Bottom-up-Lastprofilen, werden literaturbasierte Annahmen als Teil der
Technologiedaten getroffen. Im zweiten Schritt werden die Lastprofile um strukturelle Annahmen ergänzt, die
aus einem Vergleich mit den Branchenlastprofilen des Forschungsprojekts "DemandRegio" abgeleitet werden. 
Die genauen Annahmen werden von Böckmann u.a. (2021) beschrieben. Zur besseren Nachvollziehbarkeit der Modellierung
ist jede Annahme mit einem Kürzel innerhalb dieses Programms versehen. kuerzel_tabelle fasst diese Anmerkungen zusammen
und ist zusätzlich im Jupyter Notebook der entsprechenden main-Datei abgebildet.

"""

# In[FirstRun = True]


"""
First Run ist eine Hilfsvariable, die sicherstellt, dass beim "Run File (Run All)" nicht die Main-Methoden
ausgeführt werden. Zur Benutzung bitte wie folgt vorgehen:
    0. Pfad zur Input- und Output-Umgebung aktualisieren (siehe unten "Settings").
    1. Run File - Damit werden alle Excel- und SQL-Daten importiert sowie die Objekte initialisiert.
    2. Settings auf gewünschte Funktion einstellen und Zelle ausführen.
    3. Jeweilige Main Methode einzeln mithilfe "Run Cell" (Strg+Enter) ausführen.
Hinweis: Bitte zwischen den Veränderungen der Settings alle lokal gespeicherten Variablen löschen.
Idealerweise Vorgehen in der Reihenfolge der Arbeit:
    1. Lastgangsynthese | Settings: [ownAssumptions: False, doOptimize: False (Bottom-up-Lastprofile)]
    2. Lastgangsynthese | Settings: [ownAssumptions: True, doOptimize: False (Lastprofile mit strukturellen Annahmen)]
    3. Lastgangsynthese | Settings: [ownAssumptions: True, doOptimize: True (Lastprofile mit strukturellen Annahmenä
                                                                    nach einer Hyperparameteroptimierung)]
    4. Szenario - Nachfrageflexi
    
Hinweis: Alle Einheiten der Berechnung entsprechen den Einheiten der verwendeten Anwendungsbilanzen. 
Innerhalb dieser Arbeit liegen alle AWBs in PJ/a vor, weshalb die Einheit der Lastprofile zunächst ebenfalls PJ entspricht.
"""
firstRun = True

# In[Python Importe]:
"""
Alle wichtigen Pakete werden importiert.
"""

import pandas as pd
import numpy
from numpy import genfromtxt
import matplotlib.pyplot as plt
from IPython import get_ipython
import seaborn as sns
import xlsxwriter
from datetime import datetime
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import r2_score
import os
import math
import sqlalchemy
get_ipython().run_line_magic('matplotlib', 'qt')


# In[Model]:

"""
Klasse, mit der Jahresinstanzen der Gleichzeitigkeitsfaktoren erzuegt werden.

a: 96 Werte an a-Tagen
b: 96 Werte an b-Tagen
c: 96 Werte an c-Tagen
d: 365*96 Werte in Jahresreihenfolge
total: numpy.stack(datetime, schedule, jahreswerte, ...)
"""


class Model:
    def __init__(self, a, b, c, jahr, total):
        self.a = a
        self.b = b
        self.c = c
        self.jahr = jahr
        self.total = total


# In[Settings]:


"""
Hier können Verhaltenoptionen des Modells eingestellt werden. Bitte unbedingt vor dem
erstmaligen Ausführen den Pfad der Input- und Output-Dateien anpassen. Außerdem vor jedem
kompletten Ausführen des Modells (Run File) die zwischengespeicherten Variablen löschen.
Empfehlenswert ist die Ausführung einzelner Zellen, da die Importe mitunter rechenintensiv
sind und im Fall von "SQL Weather Import" einen Internetanschluss benötigen.
"""

absDemand = True   # True: Jahresverbräuche werden absolut ermittelt. False: Nur Gleichzeitigkeitsfaktoren werden in Profilen berechnet
doOutput = True   # Ob Excel-Output erzeugt werden soll, sollte bei True stehen
ownAssumptions = True   # True Bottom-up - Ob eigene Annahmen mit einbezogen werden sollen oder nicht
doOptimize = True   # True Bottom-up - Ob eine Optimisierung der Hyperparameter factSia, factDIn, factGS durchgeführt wird
defaultFactSia = 0.5    # ADefault_SIA (LambdaSIA)
defaultFactDin = 0.5    # ADefault_DIN (LambdaDIN)
defaultFactGS = {85: 0.8, 6471: 0.5, 86: 0.2, 47: 0, 55: 0.8}    # ADefault_GS (LambdaGS) - Bei 47 wird GS ohnehin nicht beachtet wegen AL_47.1 und AL_47.2 
inputEnv = 'C:/Users/xy/Excel_Input' # Bitte anpassen
outpathEnv = 'C:/Users/xy/Code'  # Bitte anpassen

# In[Rescaling Funktion]:


def rescale_to(inputlist, n):
    """
    Rescaling Funktion, die eine Liste mit linearer Interpolation auf gewünschte
    Länge streckt. In diesem Programm verwendet, um Listen mit stündlichen Werten mittels
    linearer Interpolation auf viertelstündliche Werte zu strecken.

    Parameters
    ----------
    inputlist : list
        Liste, die reskaliert werden soll.
    n : int
        Ganzzahl n, die die Länge der reskalierten Liste bestimmt.

    Returns
    -------
    out : list
          Die reskalierte Liste.

    """
    long = [0] * n
    m = len(inputlist)
    for i, x in enumerate(inputlist):
        long[i*(n)//(m)] = x

    count = 0
    for i in range(n):
        if i < n-4:
            if count == 0:
                m = long[i+4] - long[i]
                yachsenabschnitt = long[i]
            long[i] = m*count + yachsenabschnitt
            count = count + 0.25
            if count == 1:
                count = 0
        elif i >= n-4:
            long[i] = long[n-4]
    out = long
    return out


# In[Solarradiation-Influence Funktion]:


def influence_transform_sol(inputlist, i_max, i_min):
    """
    Influence Funktion - für Solarradiation: Stellt den Einfluss der Solarradiation als
    Funktion dar, mit der die Beleuchtung multipliziert werden kann. Wenig Solarradiation bildet ab
    auf 1 und viel Solarradiation auf 0. Begrenzt über maximalem Schwellenwert
    auf 0 und unter minimalem Schwellenwert auf 1. Dazwischen erfolgt eine lineare Skalierung.

    Parameters
    ----------
    inputlist : list
        Liste mit Werten der Solarradiation.
    i_max : TYPE    
        Oberer Schwellenwert, über dem die Transformation 0 abbildet.
    i_min : TYPE
        Unterer Schwellenwert, unter dem die Transformation 1 abbildet.

    Returns
    -------
    solarlist : list
        Die transformierte Funktion des Einflusses der Solarradiation auf die Beleuchtung.

    """
    solarlist = inputlist.copy()
    for i in range(len(solarlist)):
        if solarlist[i] > i_max:
            solarlist[i] = 0
        elif solarlist[i] < i_min:
            solarlist[i] = 1
        else:
            solarlist[i] = (i_max - solarlist[i])/(i_max - i_min)
    return solarlist

# In[Temperatur-Influence Funktion]:


def influence_transform_ac(inputlist):
    """
    Influence Funktion - für Temperatur (Klimakälte): Begrenzt über maximalem Schwellenwert (24) auf 1
    und unter minimalem Schwellenwert (21) auf 0.
    Dazwischen lineare Skalierung zwischen 0,6 und 1. Quelle: Ladwig, (2017), S. 51, 197

    Parameters
    ----------
    inputlist : list
        Liste der Außenlufttemperatur.

    Returns
    -------
    aclist : list
        Liste der Gleichzeitigkeitsfaktoren der Klimakälte.

    """
    aclist = inputlist.copy()
    for i in range(len(aclist)):
        if aclist[i] > 24:
            aclist[i] = 1
        elif aclist[i] < 21:
            aclist[i] = 0
        elif 21 <= aclist[i] <= 24:
            aclist[i] = (aclist[i]*(0.4/(24-21))-2.2)
    return aclist

# In[Wärme-Influence Funktion]:


def influence_transform_heating(inputlist, wz):
    """
    Influence-Funktion - für Temperatur (Raumwärme): Begrenzt über oberem Schwellenwert
    (entnommen aus DIN 18599-10) auf 0 und darunter lineare Skalierung bis 0° Celsius.

    Parameters
    ----------
    inputlist : list
        Liste der Außenlufttemperaturwerte, die transformiert werden soll.
    wz : int
        Ganzzahl des Wirtschaftsszweigs nach Klassifikation der Wirtschaftszweige (WZ 2008).

    Returns
    -------
    heatlist : list
        Liste der Gleichzeitigkeitsfaktoren der Raumwärme.

    """
    heatlist = inputlist.copy()
    if wz in {6471, 55, 47, 85, 56, 91, 90}:    # Entnommen aus DIN18599-10
        threshold = 21
    if wz == 86:
        threshold = 22
    if wz == 93:
        threshold = 19
        
    for i in range(len(heatlist)):  # ASH_2
        if 0 <= heatlist[i] and heatlist[i] < threshold:
            heatlist[i] = (heatlist[i]-threshold)/(0-threshold)
        if heatlist[i] < 0:
            heatlist[i] = 1
        if heatlist[i] >= threshold:
            heatlist[i] = 0
            
    return heatlist

# In[Annahme-Einfügen Funktion]:


def insert_assumption(inputlist, time_start, time_end, value):
    """
    Insert Funktion - um annahmenbasierte Gleichzeitigkeitsfaktoren in einen vorhandenen Lastgang
    einzufügen und den Übergang zu den Originalwerten zu glätten.
    Parameters
    ----------
    inputlist : list
        Liste der ursprünglichen Gleichzeitigkeitsfaktoren.
    time_start : float
        Zeitpunkt des Beginns der einzufügenden Annahme in Stunden.
    time_end : float
        Zeitpunkt des Endes der einzufügenden Annahme in Stunden.
    value : float
        Einzufügender Dynamisierungsfaktor während des vorgegebenen Zeitraums.
    Returns
    -------
    x : list
        Liste der neuen Gleichzeitigkeitsfaktoren.
    """
    ts = max((4*time_start)-1, 0)
    te = (4*time_end)-1
    
    x = numpy.array(inputlist, dtype='float64').copy()
    y = 0
    count = 0.25
    og_s = x[ts]
    m = float(value - og_s)
    for i in range(4):
        x[ts+y] = og_s + m*count
        x[te+y] = value + (-1*m)*count
        count = count+0.25
        y = y+1
        
    x[ts+4:te] = value
    return x


# In[Zeitraum-Durchschnitts-Funktion]:


def get_avg_resJahres(resJahresArg, tag1, tag2, sched):
    """
    get_avg_Resulting_Jahres-Funktion - berechnet die durchschnittlichen
    Lasten innerhalb eines Zeitraums.

    Parameters
    ----------
    resJahresArg : list
        Liste der Last des gesamten Jahres.
    tag1 : string
        Datum in Datetime Format, Start des zu mittelnden Zeitraums.
    tag2 : string
        Datum in Datetime Format, Ende des zu mittelnden Zeitraums.
    sched : string
        Typtag als String ('a', 'b', 'c'), über den gemittelt wird.

    Returns
    -------
    out : list
        Liste der Länge 96, also einem durchschnittlichen Tag.

    """
    out = numpy.zeros(96)
    daycount = 0
    tsTag1 = pd.Timestamp(tag1)
    tsTag2 = pd.Timestamp(tag2)
    for i in range(365):
        if i in range(tsTag1.dayofyear, tsTag2.dayofyear) and sched in resJahresArg[i*96, 1]:
            out = out + resJahresArg[i*96:(i+1)*96, 2]
            daycount = daycount+1
    out = out/daycount
    return out

# In[Create Dataframe Funktion]:


def create_DataFrame(modeltotal):
    """
    Erstellt aus einem Modell ein komplettes Pandas DataFrame mit Flags wie
    Saison, Typtag und den Querschnittstechnologien. Wird in der Funktion model_energy_demand verwendet. 

    Parameters
    ----------
    modeltotal : Model
        Eine Instanz der Klasse 'Model'.

    Returns
    -------
    datasetTotal : DataFrame
        Das komplette DataFrame.

    """
    day = pd.date_range("00:00", "23:45", freq="15min").strftime('%H:%M')
    winterA = ((get_avg_resJahres(modeltotal, '2018-01-01', '2018-02-28', 'a') +
                get_avg_resJahres(modeltotal, '2018-12-01', '2018-12-31', 'a'))/2)
    winterB = ((get_avg_resJahres(modeltotal, '2018-01-01', '2018-02-28', 'b') +
                get_avg_resJahres(modeltotal, '2018-12-01', '2018-12-31', 'b'))/2)
    winterC = ((get_avg_resJahres(modeltotal, '2018-01-01', '2018-02-28', 'c') +
                get_avg_resJahres(modeltotal, '2018-12-01', '2018-12-31', 'c'))/2)
    fhA = ((get_avg_resJahres(modeltotal, '2018-03-01', '2018-05-31', 'a') +
            get_avg_resJahres(modeltotal, '2018-09-01', '2018-11-30', 'a'))/2)
    fhB = ((get_avg_resJahres(modeltotal, '2018-03-01', '2018-05-31', 'b') +
            get_avg_resJahres(modeltotal, '2018-09-01', '2018-11-30', 'b'))/2)
    fhC = ((get_avg_resJahres(modeltotal, '2018-03-01', '2018-05-31', 'c') +
            get_avg_resJahres(modeltotal, '2018-09-01', '2018-11-30', 'c'))/2)
    sommerA = get_avg_resJahres(modeltotal, '2018-06-01', '2018-08-30', 'a')
    sommerB = get_avg_resJahres(modeltotal, '2018-06-01', '2018-08-30', 'b')
    sommerC = get_avg_resJahres(modeltotal, '2018-06-01', '2018-08-30', 'c')

    dWA = pd.DataFrame({'Zeit': day, 'Tagtyp': 'a', 'Saison': 'Winter', 'Werte': winterA})
    dWB = pd.DataFrame({'Zeit': day, 'Tagtyp': 'b', 'Saison': 'Winter', 'Werte': winterB})
    dWC = pd.DataFrame({'Zeit': day, 'Tagtyp': 'c', 'Saison': 'Winter', 'Werte': winterC})
    dFHA = pd.DataFrame({'Zeit': day, 'Tagtyp': 'a', 'Saison': 'Frühling & Herbst', 'Werte': fhA})
    dFHB = pd.DataFrame({'Zeit': day, 'Tagtyp': 'b', 'Saison': 'Frühling & Herbst', 'Werte': fhB})
    dFHC = pd.DataFrame({'Zeit': day, 'Tagtyp': 'c', 'Saison': 'Frühling & Herbst', 'Werte': fhC})
    dSA = pd.DataFrame({'Zeit': day, 'Tagtyp': 'a', 'Saison': 'Sommer', 'Werte': sommerA})
    dSB = pd.DataFrame({'Zeit': day, 'Tagtyp': 'b', 'Saison': 'Sommer', 'Werte': sommerB})
    dSC = pd.DataFrame({'Zeit': day, 'Tagtyp': 'c', 'Saison': 'Sommer', 'Werte': sommerC})

    datasetTotal = pd.concat([dWA, dWB, dWC, dFHA, dFHB, dFHC, dSA, dSB, dSC])
    return datasetTotal

# In[APE Funktion]:


def ape(y_true, y_pred):
    """
    Absolute Percentage Error Funktion - gibt einen Numpy-array der individuellen
    absoluten prozentualen Abweichung jeder Zeitscheibe zurück. Der Durchschnittswert aller APE
    ist dann der MAPE.

    Parameters
    ----------
    y_true : list
        Liste der Trainingsdaten (im Rahmen dieses Modells die Branchenlastgänge
                                  des Demand Regio Projektes).
    y_pred : list
        Liste der Testdaten (im Rahmen dieses Modells die bottom-up synthetisierten
                             Lastgänge einer Branche).

    Returns
    -------
    numpy.array
        Array der individuellen prozentualen Abweichungen.

    """
    y_true, y_pred = numpy.array(y_true), numpy.array(y_pred)

    return numpy.abs((y_true - y_pred) / y_true)

# In[MAPE Funktion]:


def mape(y_true, y_pred):
    """
    Mean Absolute Percentage Error Funktion - gibt ein Skalar der gemittelten
    absoluten prozentualen Abweichungen zurück.

    Parameters
    ----------
    y_true : list
        Liste der Trainingsdaten (im Rahmen dieses Modells die Branchenlastgänge
                                  des Demand Regio Projektes).
    y_pred : list
        Liste der Testdaten (im Rahmen dieses Modells die bottom-up synthetisierten
                             Lastgänge einer Branche).

    Returns
    -------
    float
        Skalar der gemittelten absoluten prozentualen Abweichung.

    """
    y_true, y_pred = numpy.array(y_true), numpy.array(y_pred)

    return numpy.mean(numpy.abs((y_true - y_pred) / y_true))


# In[DSM Leistungsfunktion]


def dsm_p(qst, timeMaxCapDays):
    """
    Funktion, die die Leistung der maximalen Lade- oder Entladerate - Pmax und Pmin -
    berechnet. Dazu wird der Lastgang einer Querschnittstechnologie als Argument übergeben
    und der Zeitraum definiert, aus dem die Maximalkapazität der Technologie entnommen wird.
    Hierzu eignet sich der Zeitraum eines Tages, um saisonspezifischen, also temperatur- oder
    solarradiationsabhängigen Peaks gerecht zu werden.

    Parameters
    ----------
    qst : list
        Liste des Lastgangs einer Querschnittstechnologie.
    timeMaxCapDays : int
        Ganzzahl des Zeitraums, innerhalb dessen die maximale Kapazität ausgewählt wird.

    Returns
    -------
    pmax : numpy.array
        Liste der zu jedem Zeitpunkt maximal möglichen Lasterhöhung [PJ].
    pmin : numpy.array
        Liste der zu jedem Zeitpunkt maximal möglichen Lastverringerung [PJ].

    """
    t = 24*4
    pmax = numpy.zeros(len(qst))
    pmin = numpy.zeros(len(qst))
    for i in range(len(qst)):
        y = math.floor(i/t)     # Findet die Zahl des aktuellen Tages (0-364)
        """
        Als maximale Kapazität wird die Maximallast des jeweiligen Tages verwendet
        (in anderen Veröffentlichungen wird stattdessen die maximal installierte Leistung als Maximalkapazität modelliert)
        """
        maxCap = qst[y*t:(y + timeMaxCapDays)*t].max()   
        pmax[i] = (maxCap - qst[i])
        pmin[i] = ((-1) * qst[i])
        
    return pmax, pmin


# In[DSM Energiefunktion]


def dsm_e(qst, timeframeHours):
    """
    Funktion, die den Energieinhalt des Energiespeicheräquivalents
    der DSM-Maßnahme beschreibt. Diese ist das Integral der Laderaten Pmax und Pmin über einen festgelegten
    Zeitraum der maximalen Verschiebedauer.

    Parameters
    ----------
    qst : list
        Liste des Lastgangs einer Querschnittstechnologie.
    timeframeHours : int
        Ganzzahl der Stunden der maximalen Verschiebedauer.

    Returns
    -------
    emax : numpy.array
        Maximaler Energieinhalt des Energiespeicheräquivalents der DSM-Maßnahme [PJ/4].
    emin : numpy.array
        Minimaler Energieinhalt des Energiespeicheräquivalents der DSM-Maßnahme [PJ/4].

    """
    t = timeframeHours*4
    emax = numpy.zeros(len(qst))
    emin = numpy.zeros(len(qst))
    for i in range(len(qst)):
        if (i+t) > (len(qst)-1):
            emax[i] = (qst[((len(qst)-1)-t):(len(qst)-1)].sum() / 4)
        if (i+t) <= (len(qst)-1):
            emax[i] = (qst[i:(i+t)].sum() / 4)      # geteilt durch 4, um auf Stundenwerte zu kommen
        if i < t:
            emin[i] = (-1) * (qst[(t-t):t].sum() / 4)
        if i >= t:
            emin[i] = (-1) * (qst[(i-t):i].sum() / 4)
            
    return emax, emin


# In[Excel Importe]:


"""
Import der Excel Dateien für
- Anwesenheitsprofil der ISO Norm 18523-1 (Occupancy Iso)
- Beleuchtungsprofil der ISO Norm 18523-1 (Lighting Iso)
- Anwesenheitsprofil der SIA Norm Occupancy SIA
- Anwesenheitsprofile der DIN Norm DIN 18599-10:2018-09
- Klimakälteprofil nach Ladwig, (2018)
- Kalenderdaten
- Anwendungsbilanz des Jahres 2018
- Branchenlastprofile des Forschungsprojekts "DemandRegio"
- Mechanische Energie in Krankenhäusern nach Hagemeier, (2017)
- Anwendungsbilanz Referenzenario 2035
- Anwendungsbilanz Basisszenario 2035
"""

dfLight = pd.read_excel((inputEnv+'/occupancy-iso2016energy.xlsx'),
                        sheet_name='Lighting')
dfOccIso = pd.read_excel((inputEnv+'/occupancy-iso2016energy.xlsx'),
                         sheet_name='Occupancy')
dfShares = pd.read_excel((inputEnv+'/occupancy-iso2016energy.xlsx'),
                         sheet_name='BuildingShares')
dfOccSia = pd.read_excel((inputEnv+'/occupancy-SIA2015.xlsx'),
                         sheet_name='Occupancy')
dfCal = pd.read_excel((inputEnv+'/schedule_2018_15min.xlsx'),
                      sheet_name='main')
dfOccDin = pd.read_excel((inputEnv+'/DIN18599-10.xlsx'),
                         sheet_name='Python_Export')
dfHvac = pd.read_excel((inputEnv+'/hvac-ladwig2018demand.xlsx'),
                       sheet_name='Python_Export')
dfAnwend = pd.read_excel((inputEnv+'/anwendungsbilanzen_fraunisi2015envbghd.xlsx'),
                         sheet_name='Python_Export')
dfBrLast = pd.read_excel((inputEnv+'/demandRegio_Branchenlastmodelle.xlsx'),
                         sheet_name='Tabelle1')
dfMechEn86 = pd.read_excel((inputEnv+'/mechEn-86-hagemeier2018messdaten.xlsx'),
                           sheet_name='Python_Export')
dfRefSzen = pd.read_excel((inputEnv+'/Szenarien/referenzszenario_fraunisi2017langfristM3.xlsx'),
                          sheet_name='Python_Export')
dfBasSzen = pd.read_excel((inputEnv+'/Szenarien/basisszenario_fraunisi2017langfristM3.xlsx'),
                          sheet_name='Python_Export')


"""
Typtag-Kodierung nach ISO:
a = Wochentag
b = Samstag
c = Sonntag, Feiertag
"""
# Create an empty list
lightingIsoHourly = []
occupancyIsoHourly = []
occupancySiaHourly = []
buildingSharesIso = []
buildingSharesSia = []
buildingSharesDin = []
calender = []
occupancyDinHourly = []
hvacHourly = []
ambientcool = []
ventilation = []
mechEn86Hourly = []
mechEn86A = []
mechEn86BC = []
nachtspeicherheiz = []
waermepumpe = []


for i in range((dfLight.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    lightingIsoHourly.append(list(dfLight.iloc[i, :]))

for i in range((dfOccIso.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    occupancyIsoHourly.append(list(dfOccIso.iloc[i, :]))

for i in range((dfOccSia.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    occupancySiaHourly.append(list(dfOccSia.iloc[i, :]))

# Iterate over each row in Calender
for i in range((dfCal.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    calender.append(list(dfCal.iloc[i, :]))

for i in range((dfShares.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    buildingSharesIso.append(list(dfShares.iloc[i, :]))

for i in range((dfOccDin.shape[0])):
    # Using iloc to access the values of
    # the current row denoted by "i"
    occupancyDinHourly.append(list(dfOccDin.iloc[i, :]))

for i in range((dfHvac.shape[0])):
    hvacHourly.append(list(dfHvac.iloc[i, :]))

for i in range((dfMechEn86.shape[0])):
    mechEn86Hourly.append(list(dfMechEn86.iloc[i, :]))

# Hourly in Quarterly umwandeln
occupancyIsoQuarterly = occupancyIsoHourly.copy()
for zeile in range(len(occupancyIsoQuarterly)):
    occupancyIsoQuarterly[zeile] = occupancyIsoQuarterly[zeile][:5] + rescale_to(occupancyIsoQuarterly[zeile][5:],96)

lightingIsoQuarterly = lightingIsoHourly.copy()
for zeile in range(len(lightingIsoQuarterly)):
    lightingIsoQuarterly[zeile] = lightingIsoQuarterly[zeile][:5] + rescale_to(lightingIsoQuarterly[zeile][5:],96)

occupancySiaQuarterly = occupancySiaHourly.copy()
for zeile in range(len(occupancySiaQuarterly)):
    occupancySiaQuarterly[zeile] = occupancySiaQuarterly[zeile][:3] + rescale_to(occupancySiaQuarterly[zeile][3:27],96)
    buildingSharesSia.append(occupancySiaHourly[zeile][1::26])

occupancyDinQuarterly = occupancyDinHourly.copy()
for zeile in range(len(occupancyDinQuarterly)):
    occupancyDinQuarterly[zeile] = occupancyDinQuarterly[zeile][:3]+rescale_to(occupancyDinQuarterly[zeile][3:27],96)
    buildingSharesDin.append(occupancyDinHourly[zeile][1::26])

hvacQuarterly = hvacHourly.copy()
for zeile in range(len(hvacQuarterly)):
    if hvacQuarterly[zeile][0] == "ambient_cooling":
        coolingLT = hvacQuarterly[zeile][25] #lower threshold
        coolingHT = hvacQuarterly[zeile][26] #higher threshold
        ambientcool = rescale_to(hvacQuarterly[zeile][1:25], 96)
    if hvacQuarterly[zeile][0] == "ventilation":
        ventilation = rescale_to(hvacQuarterly[zeile][1:25], 96)
    if hvacQuarterly[zeile][0] == "nachtspeicherheizung":
        nachtspeicherheiz = rescale_to(hvacQuarterly[zeile][1:25], 96)
    if hvacQuarterly[zeile][0] == "waermepumpe":
        waermepumpe = rescale_to(hvacQuarterly[zeile][1:25], 96)

for zeile in range(len(mechEn86Hourly)):
    if mechEn86Hourly[zeile][0] == "MechEnA":
        mechEn86A = rescale_to(mechEn86Hourly[zeile][1:25], 96)
    if mechEn86Hourly[zeile][0] == "MechEnBC":
        mechEn86BC = rescale_to(mechEn86Hourly[zeile][1:25], 96)

#Building Shares in Dictionary überführen
buildingSharesIsoDict = dict(numpy.array(buildingSharesIso)[:,1:3])
buildingSharesSiaDict = dict(numpy.array(buildingSharesSia))
buildingSharesDinDict = dict(numpy.array(buildingSharesDin))

# In[SQL Weather Import]:
"""
Import regionalisierter Wetterdaten aus dem Forschungsprojekt "DemandRegio"
"""

con = sqlalchemy.create_engine('postgresql://demandregio_read:read_demandregio@81.169.223.134/demandregio')  # Lesezugriff!


sql_tp_all = """ select * FROM demandregio.demandregio_temporal as a
                  join demandregio.t_nuts3_lk as b on a.id_region=b.id_ags
                  WHERE id_temporal = 11  and year_base = 2018
                  """

sql_sr_all = """ select * FROM demandregio.demandregio_temporal as a
                  join demandregio.t_nuts3_lk as b on a.id_region=b.id_ags
                  WHERE id_temporal = 17  and year_base = 2018

                  """


tp_sql = pd.read_sql(sql_tp_all, con)  # tp stands for temperature
sr_sql = pd.read_sql(sql_sr_all, con)  # sr stands for solar radiation

tp_sql["ags_lk"] = tp_sql["ags_lk"].astype(float)
sr_sql["ags_lk"] = sr_sql["ags_lk"].astype(float)

bzeLK = pd.read_excel((inputEnv+'/BZEjeLK.xlsx'), sheet_name='BZEjeLK.xlsx')
bzeLK.loc[88] = bzeLK.sum()

for zeile in range(0, bzeLK.shape[0]):
    summe = bzeLK.iloc[zeile, 1]
    for spalte in bzeLK:
        if spalte != "WZ" and spalte != "SUM":
            bzeLK[spalte][zeile] = numpy.divide(bzeLK[spalte][zeile], (summe))  # Anteile der Landkreise an GesamtBZE der WZ

bzeLK = bzeLK.loc[88]

temperatureHourly = numpy.zeros(365*24)
globalSolar = numpy.zeros(365*24*4)

for lk in sr_sql['ags_lk']:
    if lk in bzeLK.index:
        tp_lk = numpy.asarray(numpy.array(tp_sql.loc[(tp_sql['ags_lk'] == lk) &
                               (tp_sql['internal_id'].astype('str') == '[1]') &
                               (tp_sql['year_base'] == 2018)]['values'])[0])

        tp_lk = tp_lk * bzeLK[int(lk)]
        temperatureHourly = temperatureHourly+ tp_lk


        sr_lk = numpy.asarray(numpy.array(sr_sql.loc[(sr_sql['ags_lk'] == lk) &
                                       (tp_sql['year_base'] == 2018)]['values'])[0])

        sr_lk = sr_lk * bzeLK[int(lk)]
        globalSolar = globalSolar + sr_lk


temperature = temperatureHourly.copy()
temperature = numpy.repeat(temperatureHourly, 4)
for j in range((365*24)-1):
    y = temperature[j*4+4]
    x = temperature[j*4]
    k = (y - x)/4
    temperature[(j*4)+1] = x + (k*1)
    temperature[(j*4)+2] = x + (k*2)
    temperature[(j*4)+3] = x + (k*3)


# In[Calendar]:

npcal = numpy.array(calender)

"""
Hinzufügen der Datums- und Zeittagsinformationen
"""

dateTime = npcal[:, 5]

counter = 0
for i in range(len(dateTime)):
    dateTime[i] = dateTime[i] + pd.Timedelta(minutes=15*counter)
    counter = counter+1
    if counter == 96:
        counter = 0

schedule = npcal[:, 7]

tm = []
for i in range(35040):
    tm.append(npcal[i, 5].strftime(format="%H:%M"))
time = numpy.array(tm)

dte = []
for i in range(35040):
    dte.append(npcal[i, 5].strftime(format="%Y-%m-%d"))
date = numpy.array(dte)

wd = []
for i in range(35040):
    wd.append(datetime.strptime(date[i], "%Y-%m-%d").isoweekday())
weekday = numpy.array(wd)

seas = []
for i in range(35040):
    if i <= (58*96) or i> (333*96): #Zahl der Tage ausgerechnet und mal Viertelstunden genommen
        seas.append("Winter")
    elif (58*96)<i<(151*96) or (242*96)<i<(334*96):
        seas.append("Frühling u Herbst")
    elif (150*96)<i<(243*96):
        seas.append("Sommer")
season = numpy.array(seas)



# In[Occupancy]:



def model_occupancy_profile(wz,factSia, factDin):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Anwesenheiten.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    factSia : float
        Anteil zwischen SIA und ISO Normen, begrenzt auf Intervall [0,1]. (LambdaSIA)
    factDin : float
        Anteil der Minderung von Anwesenheiten außerhalb der DIN Norm, begrenzt auf Intervall [0,1].(LambdaDIN)

    Returns
    -------
    occModel : Model
        Instanz der "Model"-Klasse. Enthält Anwesenheitsprofile nach Typtagkodierung
        sowie für das gesamte Jahr 2018.

    """
    npOccSia = numpy.array(occupancySiaQuarterly).copy()
    npOccIso = numpy.array(occupancyIsoQuarterly).copy()
    npOccIsofloat = numpy.array(npOccIso[:, 5:].copy(), dtype='float64')
    npOccDin = numpy.array(occupancyDinQuarterly).copy()
    npOccDinfloat = numpy.array(npOccDin[:, 3:].copy(), dtype='float64')
    npOccSiafloat = numpy.array(npOccSia[:, 3:].copy(), dtype='float64')
    occDin = []
    """
    Wirtschaftszweig auswählen und über mehrere mitteln für DIN
    """
    for i in range(len(npOccDin)):
        if float(npOccDin[i, 2]) == wz:
            occDin.append(list(float(buildingSharesDinDict[npOccDin[i, 1]])*npOccDinfloat[i, :]))
    npOccDin = numpy.array(occDin)
    npOccDin = numpy.array(numpy.sum(npOccDin, axis=0))
    """
    Occupancy Iso
    """
    occIsoA = []
    occIsoB = []
    occIsoC = []
    for i in range(len(npOccIso)):
        if float(npOccIso[i, 4]) == wz and npOccIso[i, 2] == 'a':
            occIsoA.append(list(float(buildingSharesIsoDict[npOccIso[i, 1]])*npOccIsofloat[i, :]))
        if float(npOccIso[i, 4]) == wz and npOccIso[i, 2] == 'b':
            occIsoB.append(list(float(buildingSharesIsoDict[npOccIso[i, 1]])*npOccIsofloat[i, :]))
        if float(npOccIso[i, 4]) == wz and npOccIso[i, 2] == 'c':
            occIsoC.append(list(float(buildingSharesIsoDict[npOccIso[i, 1]])*npOccIsofloat[i, :]))
    np_occA = numpy.array(occIsoA).astype(numpy.float)
    np_occB = numpy.array(occIsoB).astype(numpy.float)
    np_occC = numpy.array(occIsoC).astype(numpy.float)
    if len(occIsoA) > 1:
        occIsoA = numpy.array(numpy.sum(np_occA, axis=0))
        occIsoB = numpy.array(numpy.sum(np_occB, axis=0))
        occIsoC = numpy.array(numpy.sum(np_occC, axis=0))
    elif len(occIsoA) == 1:
        occIsoA = np_occA
        occIsoB = np_occB
        occIsoC = np_occC
    occIsoJahrList = []
    for i in range(365):
        if schedule[i*96] == 'a':
            occIsoJahrList.extend(float(i) for i in occIsoA)
        if schedule[i*96] == 'b':
            occIsoJahrList.extend(float(i) for i in occIsoB)
        if schedule[i*96] == 'c':
            occIsoJahrList.extend(float(i) for i in occIsoC)
    occIsoJahr = numpy.array(occIsoJahrList).astype(numpy.float)
    """
    Occupancy aus Iso mit reinnehmen und mit SIA vermengen
    """
    occSiaList = []
    for i in range(len(npOccSia)):
        if float(npOccSia[i, 2]) == wz:
            occSiaList.append(list(float(buildingSharesSiaDict[npOccSia[i,1]])*npOccSiafloat[i, :]))
    np_occSia = numpy.array(occSiaList)
    occSiaA = numpy.array(numpy.sum(np_occSia, axis= 0))
    """
    Elemente von DIN Anwesenheiten ändern 1->0 und 0->1
    """
    npOccDin = (1-npOccDin)
    occSiaIsoA = ((factSia*occSiaA) + ((1-factSia)*occIsoA))  # Mischung aus SIA und ISO
    occSiaIsoA = occSiaIsoA - ((factDin*npOccDin)*occSiaIsoA)
    occIsoB = occIsoB - ((factDin*npOccDin)*occIsoB)
    occIsoC = occIsoC - ((factDin*npOccDin)*occIsoC)
    
    
    """
    Annahmen einbauen
    """
    if wz == 47:
        if ownAssumptions:
            occIsoB = occSiaIsoA    # AO_47.2

    if wz == 6471:
        occIsoB = insert_assumption(occIsoB, 8, 19, 0.3).copy()  # AO_6471.1
        occIsoB = insert_assumption(occIsoB, 19, 23, 0).copy()

    if wz == 47:
        for i in range(len(occIsoC)):
            if occIsoC[i] > 0:
                if ownAssumptions:
                    occIsoC[i] = 0   # AO_47.1

    if wz == 85:
        if ownAssumptions:
            occIsoB = occIsoC   # AO_85.1
            occSiaIsoA[4*12:4*15] = numpy.clip(occSiaIsoA[4*12:4*15], 0, 0.9) # AO_85.2
            
    if wz == 55:
        if ownAssumptions:
            occIsoB = occSiaIsoA   # AO_55.1
            occIsoC = occSiaIsoA

    occSiaIsoJahrList = []
    for i in range(365):
        if schedule[i*96] == 'a':
            occSiaIsoJahrList.extend(float(i) for i in occSiaIsoA)
        if schedule[i*96] == 'b':
            occSiaIsoJahrList.extend(float(i) for i in occIsoB)
        if schedule[i*96] == 'c':
            occSiaIsoJahrList.extend(float(i) for i in occIsoC)
    occJahr = numpy.array(occSiaIsoJahrList).astype(numpy.float)

    occTotal = numpy.stack((date, time, weekday, season, schedule, occJahr), axis=-1)

    occModel = Model(occSiaIsoA, occIsoB, occIsoC, occJahr, occTotal)

    return occModel



# In[Lighting]:

globSol = influence_transform_sol(globalSolar, 40, 20)
def model_lighting_demand(wz, occModel, factGS, anwBil):
    
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Beleuchtung aus.
    - Wetter (Global Solar)
    - Jahresgesamtverbrauch Strom Beleuchtung GHD aus Anwendungsbilanz/Szenario
    - Wirtschaftszweig
    
    Achtung, anwBil muss DataFrame sein, eingelesen per excel

    Parameters
    ----------
     wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    factGS : float
        Anteil des Einflusses der Solarstrahlung auf die Beleuchtung (LambdaGS), begrenzt auf dem Intervall [0,1].
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    lightModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur Beleuchtung [PJ].

    """

    #Achtung! Standardisieren - und dann alle faktoren mit täglichem Durchschnittsverbrauch multiziplieren
    anwBel = float(anwBil.loc[anwBil['WZ'] == wz, 'Beleuchtung'])
    jahresBel = numpy.array([anwBel/(365*96)] * (365*96))
    npLight = numpy.array(lightingIsoQuarterly).copy()
                                                                                                                #-> devJahr
    lightA = numpy.array(occModel.a).copy()
    lightB = numpy.array(occModel.b).copy()
    lightC = numpy.array(occModel.c).copy()
    """
    Annahmen einfügen
    """
    if wz == 6471:
        if ownAssumptions:
            lightA[4*10:4*14] = numpy.clip(lightA[4*10:4*14], 0.9, 1)  # AL_6471.2
        for i in range(69, 79): #17.25*4,19.75*4 #AL_6471.3
            lightA[i] = lightA[i-1]-0.039   # stetige Abnahme bis 19:30 auf 0.2
        for i in range(79, 93):
            lightA[i] = lightA[i-1]-0.017   # stetige Abnahme bis 23h (Verkehrsflächen)
        for i in range(5*4, 29):
            lightA[i] = lightA[i-1]+0.029  # morgendlicher Anstieg in einigen Betrieben
    if wz == 55:                            # AL_55.1
        lightA = insert_assumption(lightA, 1, 6, 0.2).copy()
        lightB = insert_assumption(lightB, 1, 6, 0.2).copy()
        lightC = insert_assumption(lightC, 1, 6, 0.2).copy()
    if wz == 85:
        if ownAssumptions:
            lightA[4*10:4*14] = numpy.clip(lightA[4*10:4*14], 0.9,1) # AL_85.1
            lightA[57] = 0.8
    if wz == 47:
        smoothing = {1: 0.25, 2: 0.4, 3: 0.6, 4: 0.75}
        for lst in [lightA, lightB, lightC]:
            count = 0
            for i in range(len(lst)):
                if lst[i] > 0.1:    # to enable effects of AL_47.1
                    count = count + 1
                    if count <= 4:   # AL_47.1
                        lst[i] = smoothing[count]
                    else:
                        lst[i] = 1      # AL_47.2
                        
    if wz == 86:                            # AL_86.1
        lightA = insert_assumption(lightA, 0, 6, 0.2).copy()
        lightB = insert_assumption(lightA, 0, 6, 0.2).copy()
        lightC = insert_assumption(lightA, 0, 6, 0.2).copy()
        lightA = insert_assumption(lightA, 22, 0, 0.2).copy()
        lightB = insert_assumption(lightA, 22, 0, 0.2).copy()
        lightC = insert_assumption(lightA, 22, 0, 0.2).copy()
        lightA[23*4:] = 0.2
        lightA[:4] = 0.2  
        lightB[:4] = 0.2  
        lightC[:4] = 0.2  
        lightB[23*4:] = 0.2
        lightC[23*4:] = 0.2
        lightA[0:4] = 0.2
        lightB[0:4] = 0.2
        lightC[0:4] = 0.2


    """
    Jahresprofil erstellen
    """
    lightJahrList = []
    for i in range(365):
        if schedule[i*96] == 'a':
            lightJahrList.extend(float(i) for i in lightA)
        if schedule[i*96] == 'b':
            lightJahrList.extend(float(i) for i in lightB)
        if schedule[i*96] == 'c':
            lightJahrList.extend(float(i) for i in lightC)
    lightJahr = numpy.array(lightJahrList).astype(numpy.float)


    productLight = (lightJahr)+(lightJahr*globSol*factGS)
    dynFacBel = productLight/numpy.amax(productLight)

    if wz == 47: #AL_47.3, AL_55.2,
        for i in range(len(dynFacBel)):
            if dynFacBel[i] < 0.05:
                dynFacBel[i] = 0.05 

    if wz == 85  or wz == 55: #AL_85.2
        for i in range(len(dynFacBel)):
            if dynFacBel[i] < 0.15:
                dynFacBel[i] = 0.15

    if wz == 6471: #AL_6471.4
        for i in range(len(dynFacBel)):
            if dynFacBel[i] < 0.2:
                dynFacBel[i] = 0.2

    if absDemand is True:
        resJahresBel = (sum(jahresBel) / sum(dynFacBel)) * dynFacBel
    else:
        resJahresBel = dynFacBel.copy()

    # komplette Matrix: 0=Datum u Zeit, 1=schedule, 2=resJahresBel
    resBelTotal = numpy.stack((date, time, weekday, season, schedule, resJahresBel), axis=-1)
    lightModel = Model(lightA, lightB, lightC, resJahresBel, resBelTotal)

    return lightModel


# In[AC]:

dummy = numpy.zeros(96)
acTemp = influence_transform_ac(temperature)
npAC = numpy.array(ambientcool).copy()
def model_ambient_cooling_demand(wz, occModel, anwBil):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Klimakälte.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    acModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur Klimakälte [PJ].

    """


    anwKlimaK = float(anwBil.loc[anwBil['WZ'] == wz, 'Klimakälte'])
    jahresKlimaK = numpy.array([anwKlimaK/(365*96)] * (365*96))

    acJahrList = []
    for i in range(365):
        acJahrList.extend(float(i) for i in npAC)
    acJahr = numpy.array(acJahrList)

    productAC = (acJahr * acTemp) * occModel.jahr
    dynFacAC = productAC/numpy.amax(productAC)
    if absDemand == True:
        resAC = dynFacAC*(sum(jahresKlimaK)/sum(dynFacAC))
    else:
        resAC = dynFacAC.copy()

    resACTotal = numpy.stack((date, time, weekday, season, schedule, resAC), axis=-1)
    acModel = Model(dummy, dummy, dummy, resAC, resACTotal)


    return acModel

# In[Prozesskälte]:
dummy = numpy.zeros(96)
def model_process_cooling_demand(wz, occModel, anwBil):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Prozesskälte.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    pcoolModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur Prozesskälte [PJ].


    """
    
    anwProzK = float(anwBil.loc[anwBil['WZ'] == wz, 'Prozesskälte'])
    jahresProzK = numpy.array([anwProzK/(365*96)] * (365*96))

    pcoolA = numpy.array(occModel.a).astype(float).copy()
    pcoolB = numpy.array(occModel.b).astype(float).copy()
    pcoolC = numpy.array(occModel.c).astype(float).copy()

    for lst in [pcoolA, pcoolB, pcoolC]:
        for i in range(len(lst)):
            if lst[i] > 0:
                lst[i] = 1
            if lst[i] == 0:
                if wz == 47:
                    lst[i] = 0.7    #APC_47.1
                else:
                    lst[i] = 0.8    #APC_1

    pcoolB = pcoolB*0.95    #APC_2
    pcoolC = pcoolC*0.9     #APC_3

    for lst in [pcoolA, pcoolB, pcoolC]:
        for i in range(len(lst)):   #APCSH_1
            if i < (len(lst)-4):
                if (lst[i+1] > lst[i] and lst[i] == lst[i-1]):
                    lst[i+1] = lst[i]+ (0.25*(lst[i+4] - lst[i]))
                    lst[i+2] = lst[i]+ (0.5*(lst[i+4] - lst[i]))
                    lst[i+3] = lst[i]+ (0.75*(lst[i+4] - lst[i]))
                if (lst[i+1] < lst[i] and lst[i] == lst[i-1]):
                    lst[i+1] = lst[i] - (0.5*(lst[i]-lst[i+3]))
                    lst[i+2] = lst[i] - (0.75*(lst[i]-lst[i+3]))
                    lst[i] = lst[i] - (0.25*(lst[i]-lst[i+3]))

    """
    Date        No. of Day
    31.01.2018	30
    28.02.2018	58
    31.05.2018	150
    31.08.2018	242
    30.11.2018	333
    31.12.2018  365
    """

    pcoolJahrList = []
    for i in range(365):
        if schedule[i*96] == 'a':
            temp = pcoolA
        if schedule[i*96] == 'b':
            temp = pcoolB
        if schedule[i*96] == 'c':
            temp = pcoolC
        if i <= 58 or i> 333: #Winter
            temp = temp * 0.8   #APC_4
        if 58<i<151 or 242<i<334: #Übergang
            temp = temp * 0.9
        pcoolJahrList.extend(temp)
    pcoolJahr = numpy.array(pcoolJahrList)

    dynFacPcool = pcoolJahr/numpy.amax(pcoolJahr)
    if absDemand == True:
        resAC = dynFacPcool*(sum(jahresProzK)/sum(dynFacPcool))
    else:
        resAC = dynFacPcool.copy()

    pcoolTotal = numpy.stack((date, time, weekday, season, schedule, resAC), axis=-1)
    pcoolModel = Model(pcoolA, pcoolB, pcoolC, resAC, pcoolTotal)
    return pcoolModel


# In[Raumwärme]:
npNSH = numpy.array(nachtspeicherheiz)
npWP = numpy.array(waermepumpe)

def model_space_heating_demand(wz, occModel, anwBil, wpshare):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Raumwärme und Warmwasser.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).
    wpshare : float
        Anteil der Wärmepumpen, begrenzt auf dem Intervall [0,1].

    Returns
    -------
    heatModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zu Raumwärme und Warmwasser [PJ].

    """
    
    npHeat = ((wpshare * npWP)+( (1-wpshare) * npNSH))
    anwHeat = float(anwBil.loc[anwBil['WZ'] == wz, 'Raumwärme und Warmwasser'])
    jahresHeat = numpy.array([anwHeat/(365*96)] * (365*96))

    waterA = occModel.a.copy()
    waterB = occModel.b.copy()
    waterC = occModel.c.copy()

    heatJahrList = []
    for i in range(365):
        heatJahrList.extend(float(i) for i in npHeat)
    heatJahr = numpy.array(heatJahrList)

    for lst in [waterA, waterB, waterC]:
        for i in range(len(lst)):
            if lst[i] > 0:
                lst[i] = 1

    waterJahrList = []
    for i in range(365):
        if schedule[i*96] == 'a':
            waterJahrList.extend(float(i) for i in waterA)
        if schedule[i*96] == 'b':
            waterJahrList.extend(float(i) for i in waterB)
        if schedule[i*96] == 'c':
            waterJahrList.extend(float(i) for i in waterC)
    waterJahr = numpy.array(waterJahrList).astype(numpy.float)

    for i in range(len(waterJahr)):  #APCSH_1
        if i < (len(waterJahr)-4):
            if (waterJahr[i] == 0 and waterJahr[i+1]>0):
                waterJahr[i+1] = 0.25*waterJahr[i+4]
                waterJahr[i+2] = 0.5*waterJahr[i+4]
                waterJahr[i+3] = 0.75*waterJahr[i+4]
            if (waterJahr[i] > 0 and waterJahr[i+1] == 0):
                waterJahr[i] = 0.25*waterJahr[i-3]
                waterJahr[i-1] = 0.5*waterJahr[i-3]
                waterJahr[i-2] = 0.75*waterJahr[i-3]

    tempinf = influence_transform_heating(temperature, wz)  # ASH_2
    productHeat = (0.3*(heatJahr * tempinf)) + (0.7*waterJahr)# ASH_1

    dynFacHeat = productHeat/numpy.amax(productHeat)
    if absDemand == True:
        resHeat = dynFacHeat*(sum(jahresHeat)/sum(dynFacHeat))
    else:
        resHeat = dynFacHeat.copy()

    heatTotal = numpy.stack((date, time, weekday, season, schedule, resHeat), axis=-1)
    heatModel = Model(dummy, dummy, dummy, resHeat, heatTotal)
    return heatModel

# In[Mechanical]:

def model_mechenergy_demand(wz, occModel, anwBil):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der mechanischen Energie.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    mechModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur mechanischen Energie [PJ].

    """
    
    
    handelA = numpy.array(occModel.a).copy()
    handelB = numpy.array(occModel.b).copy()
    handelC = numpy.array(occModel.c).copy()

    for lst in [handelA, handelB, handelC]:
        for i in range(len(lst)):
            if lst[i] > 0:    # to enable effects of AM_47.1
                lst[i] = 0.76
            else:
                lst[i] = 0

    vent = numpy.array(ventilation).copy()
    anwMech = float(anwBil.loc[anwBil['WZ'] == wz, 'Mechanische Energie'])
    jahresMech = numpy.array([anwMech/(365*96)] * (365*96))

    mEA = numpy.array(mechEn86A).copy()
    mEB = numpy.array(mechEn86BC).copy()
    mEC = numpy.array(mechEn86BC).copy()

    vent = 0.24*vent    # AM_1
    mEA = 0.76*mEA
    mEB = 0.76*mEB
    mEC = 0.76*mEC
    if wz == 86:
        mechEnA = (mEA + vent)
        mechEnB = (mEB + vent)
        mechEnC = (mEC + vent)
        mechEnL = []
        for i in range(365):
            if schedule[i*96] == 'a':
                mechEnL.extend(float(i) for i in mechEnA)
            if schedule[i*96] == 'b':
                mechEnL.extend(float(i) for i in mechEnB)
            if schedule[i*96] == 'c':
                mechEnL.extend(float(i) for i in mechEnC)
        mechEnList = numpy.array(mechEnL).astype(numpy.float)

    if wz == 47:
        if ownAssumptions:
            mechEnHA = (handelA + vent) 
            mechEnHB = (handelB + vent)
            mechEnHC = (handelC + vent)
            mechEnHL = []
            for i in range(365):
                if schedule[i*96] == 'a':
                    mechEnHL.extend(float(i) for i in mechEnHA)
                if schedule[i*96] == 'b':
                    mechEnHL.extend(float(i) for i in mechEnHB)
                if schedule[i*96] == 'c':
                    mechEnHL.extend(float(i) for i in mechEnHC)
            mechEnList = numpy.array(mechEnHL).astype(numpy.float)
        if not ownAssumptions:
            mechEn = numpy.ones(96)*0.76
            mechEn = mechEn + vent
            mechEnList = []
            for i in range(365):
                mechEnList.extend(float(i) for i in mechEn)


    if wz != 86 and wz !=55 and wz !=47:
        mechEn = numpy.ones(96)*0.76
        mechEn = mechEn + vent
        mechEnList = []
        for i in range(365):
            mechEnList.extend(float(i) for i in mechEn)
            
    if wz == 55: 
        mechEn = numpy.ones(96)*0.5*0.76 # AM_55.1
        mechEn[40:68] = 0.76
        z=0
        tempcount = 0.125
        incl = 0.38
        for i in range(8):
            mechEn[33+z] = 0.38 + incl*tempcount
            mechEn[68+z] = 0.76 + (-1*incl)*tempcount
            tempcount = tempcount+0.125
            z = z+1
        mechEn = mechEn + vent
        mechEnList = []
        for i in range(365):
            mechEnList.extend(float(i) for i in mechEn)

    productMech = numpy.array(mechEnList)
    dynFacMech = productMech/numpy.amax(productMech)
    if absDemand == True:
        resMechEn = productMech*(sum(jahresMech)/sum(dynFacMech))
    else:
        resMechEn = productMech.copy()

    mechTotal = numpy.stack((date, time, weekday, season, schedule, resMechEn), axis=-1)
    mechModel = Model(dummy, dummy, dummy, resMechEn, mechTotal)
    return mechModel

# In[IKT]:

def model_ikt_demand(wz, occModel, anwBil):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der IKT.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    iktModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur IKT [PJ].

    """

    if wz != 47 and wz != 6471 and wz != 85:
        iktJahr = numpy.ones(35040)

    if wz == 47 or wz == 6471 or wz == 85:
        iktA = occModel.a.copy()
        iktB = occModel.b.copy()
        iktC = occModel.c.copy()
        for lst in [iktA, iktB, iktC]:
            for i in range(len(lst)):
                if lst[i] > 0:
                    lst[i] = 1
                if lst[i] == 0:
                    if wz == 47 and ownAssumptions:
                        lst[i] = 0.2 #AIKT_47.1
                    if wz == 6471 or wz == 85:
                        lst[i] = 0.6 #AIKT_6471, AIKT_85

        for lst in [iktA, iktB, iktC]:
            for i in range(len(lst)):   #APCSH_1
                if i < (len(lst)-4):
                    if (lst[i+1] > lst[i] and lst[i] == lst[i-1]):
                        lst[i-1] = lst[i]+ (0.5*(lst[i+4] - lst[i]))
                        lst[i-2] = lst[i]+ (0.25*(lst[i+4] - lst[i]))
                        lst[i] = lst[i]+ (0.75*(lst[i+4] - lst[i]))
                    if (lst[i+1] < lst[i] and lst[i] == lst[i-1]):
                        lst[i-1] = lst[i] - (0.5*(lst[i]-lst[i+1]))
                        lst[i-2] = lst[i] - (0.25*(lst[i]-lst[i+1]))
                        lst[i] = lst[i] - (0.75*(lst[i]-lst[i+1]))

        iktJahrList = []
        for i in range(365):
            if schedule[i*96] == 'a':
                iktJahrList.extend(float(i) for i in iktA)
            if schedule[i*96] == 'b':
                iktJahrList.extend(float(i) for i in iktB)
            if schedule[i*96] == 'c':
                iktJahrList.extend(float(i) for i in iktC)
        iktJahr = numpy.array(iktJahrList).astype(numpy.float)



    if wz == 47 and ownAssumptions == False:
        iktJahr = numpy.ones(35040)

    anwIKT = float(anwBil.loc[anwBil['WZ'] == wz, 'IuK'])
    jahresIKT = numpy.array([anwIKT/(365*96)] * (365*96))

    dynFacIKT = iktJahr/numpy.amax(iktJahr)
    if absDemand == True:
        resIKT = iktJahr*(sum(jahresIKT)/sum(dynFacIKT))
    else:
        resIKT = dynFacIKT.copy()

    iktTotal = numpy.stack((date, time, weekday, season, schedule, resIKT), axis= -1)
    iktModel = Model(dummy, dummy, dummy, resIKT, iktTotal)
    return iktModel

# In[Prozesswärme]:

def model_processHeat_demand(wz, occModel, anwBil):
    """
    Modellierung der Gleichzeitigkeitsfaktoren der Prozesswärme.

    Parameters
    ----------
    wz : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).
    occModel : Model
        Anwesenheitsmodell.
    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).

    Returns
    -------
    procHModel : Model
        Instanz der Klasse "Model" mit Lastprofilen zur Prozesswärme [PJ].

    """
    procHJahr = numpy.ones(35040).astype(numpy.float)
    if wz == 47:
        procHA = occModel.a.copy()
        procHB = occModel.b.copy()
        procHC = occModel.c.copy()
        for lst in [procHA, procHB, procHC]:
            for i in range(len(lst)):
                if lst[i] > 0:  #APH_47.1
                    lst[i] = 1
                if lst[i] == 0:
                    lst[i] = 0.2
        

        procHJahrList = []
        for i in range(365):
            if schedule[i*96] == 'a':
                procHJahrList.extend(float(i) for i in procHA)
            if schedule[i*96] == 'b':
                procHJahrList.extend(float(i) for i in procHB)
            if schedule[i*96] == 'c':
                procHJahrList.extend(float(i) for i in procHC)
        procHJahr = numpy.array(procHJahrList).astype(numpy.float)
        
    if wz == 55:
        if ownAssumptions:
            procH = numpy.ones(96)
            procH = insert_assumption(procH, 0, 5, 0.2).copy()  # APH_55.1
            procHJahrList = []
            for i in range(365):
                    procHJahrList.extend(float(i) for i in procH)
            procHJahr = numpy.array(procHJahrList).astype(numpy.float)


    anwprocH = float(anwBil.loc[anwBil['WZ'] == wz, 'Sonstige Prozesswärme'])
    jahresProcH = numpy.array([anwprocH/(365*96)] * (365*96))

    dynFacProcH = procHJahr/numpy.amax(procHJahr)
    if absDemand == True:
        resPH = procHJahr*(sum(jahresProcH)/sum(dynFacProcH))
    else:
        resPH = dynFacProcH.copy()

    procHTotal = numpy.stack((date, time, weekday, season, schedule, resPH), axis= -1)
    procHModel = Model(dummy,dummy,dummy, resPH, procHTotal)
    return procHModel

# In[TotalModel]:


def model_energy_demand(wz_mod, factSia, factDin, factGS, anwBil, df, compare, wpshare):
    """
    Übergreifende Funktion, die mit Angabe aller Parameter die Funktionen der Gleichzeitigkeitsfaktoren
    aufruft und in ein gemeinsames Modell zusammenfügt.

    Parameters
    ----------
    wz_mod : int
        Ganzzahl des Wirtschaftszweigs (6471, 47, 55, 86, 85).    
    factSia : float
        Anteil zwischen SIA und ISO Normen, begrenzt auf Intervall [0,1]. (LambdaSIA)
    factDin : float
        Anteil der Minderung von Anwesenheiten außerhalb der DIN Norm, begrenzt auf Intervall [0,1].(LambdaDIN)
    
    factGS : float
        Anteil des Einflusses der Solarstrahlung auf die Beleuchtung (LambdaGS), begrenzt auf dem Intervall [0,1].

    anwBil : DataFrame
        Anwendungsbilanz (Bspw. 2018 oder die Szenarien für 2035).
    df : Boolean
        True: DataFrame wird zurückgegeben. Falls: Nur der R^2-Score wird zurückgegeben
    compare : Boolean
        Entscheidet, ob ein Vergleich mit Branchenlastprofilen stattfinden soll.
    wpshare : float
        Anteil der Wärmepumpen an der Raumwärme im betrachteten Jahr.

    Returns
    -------
    float/DataFrame
        Gibt entweder float "Score" zurück, oder das gesamte DataFrame.

    """

    Mod_occ = model_occupancy_profile(wz_mod, factSia, factDin)
    outDF = pd.DataFrame(data = Mod_occ.total, columns = ["Date", "Time", "Wochentag", "Saison", "Tagtyp", "Anwesenheit"])
    outDF["Beleuchtung"] = model_lighting_demand(wz_mod, Mod_occ, factGS, anwBil).jahr
    outDF["Klimakälte"] = model_ambient_cooling_demand(wz_mod, Mod_occ, anwBil).jahr
    outDF["Prozesskälte"] = model_process_cooling_demand(wz_mod, Mod_occ, anwBil).jahr
    outDF["Raumwärme und Warmwasser"] = model_space_heating_demand(wz_mod, Mod_occ, anwBil, wpshare).jahr
    outDF["Mechanische Energie"] = model_mechenergy_demand(wz_mod, Mod_occ, anwBil).jahr
    outDF["IKT"] = model_ikt_demand(wz_mod, Mod_occ, anwBil).jahr
    outDF["Sonstige Prozesswärme"] = model_processHeat_demand(wz_mod, Mod_occ, anwBil).jahr

    # Alle QSTs summieren
    gesamt = (outDF["Beleuchtung"] + outDF["Klimakälte"] + outDF["Prozesskälte"] +
              outDF["Raumwärme und Warmwasser"] + outDF["Mechanische Energie"] +
              outDF["IKT"] + outDF["Sonstige Prozesswärme"])
    outDF["GesamtPred"] = gesamt

    anwGes = anwBil.loc[anwBil['WZ'] == wz_mod, 'Gesamt'].values[0]

    if compare:
        outDF["Branchenlast"] = dfBrLast[wz_mod].copy()

        #Branchenlast an Anwendungsbilanzsumme skalieren
        outDF["Branchenlast"] = (outDF["Branchenlast"]*
                                 (1+(anwGes-outDF["Branchenlast"].sum()) / outDF["Branchenlast"].sum()))
        apeOut = ape(outDF["Branchenlast"].to_numpy(), outDF["GesamtPred"].to_numpy())
        outDF["APE"] = apeOut
        outDF = outDF.reset_index()
        score_err = r2_score(outDF["Branchenlast"].to_numpy(), outDF["GesamtPred"].to_numpy())
        outDF["R2"] = score_err
        score = numpy.array([score_err, factSia, factDin, factGS])
        if df:
            return outDF
        else:
            return score
    else:
        return outDF

# In[Main: Lastgangsynthese]
"""
Hauptmethode für das erste Modul der Arbeit: Branchen- und technologiespezifische Lastprofile.

Erstellt einen Ausgabeordner und ordnet den Excel-Dateien ein Datum und einen Dateinamen je Modellschritt zu.
    1. Modellierungsschritt: Bottom-up-Lastprofile  -- ohne Namenszusatz nach Datum
    2. Modellierungsschritt: Lastprofile inkl. Annahmen -- Namenszusatz "Annahmen"
    3. Modellierungsschritt: Lastprofile inkl. Annahmen und Hyperparameteroptimierung
                                            -- Namenszusatz "Annahmen_Opti"
"""

if not firstRun:
    """
    Dateiname und -pfad wird erstellt.
    """
    
    now = datetime.now()
    date_time = now.strftime("%d%m%Y-%H-%M-%S")
    outpath = outpathEnv + ("/Results_" + date_time)
    bestParams = {}
    if ownAssumptions:
        outpath = outpath + str("_Annahmen")
    if doOptimize:
        outpath = outpath + str("_Opti/")
    if ownAssumptions is True and doOptimize is False:
        outpath = outpath + str("/")
    if ownAssumptions is False and doOptimize is False:
        outpath = outpath + str("/")

    if not os.path.exists(outpath):
        os.makedirs(outpath)
    for wz_out in [6471, 55, 86, 85, 47]:
        syntheseworking = True
        if doOptimize:
            """
            Hyperparameteroptimierung auf entsprechendem Grid
            """
            param_grid = {'fSia': [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
                          'fDin': [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
                          'fGS': [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]}

            grid = ParameterGrid(param_grid)

            res = []
            ct = 0
            for params in grid:
                res.append(model_energy_demand(wz_out, params['fSia'], params['fDin'], params['fGS'],
                                               dfAnwend, False, True, 0.25))  # ASH_3 Anteil der Wärmepumpen 2018 bei 25%
                perc = float(round((ct/1331)*100, 2))  # 11^3 = 1331 (Parametergrid)
                x = "Progress: " + str(perc) + "%"
                print("\r" + x, end=' ')
                ct = ct+1
            param_results = numpy.array(res)

            index = numpy.where(param_results[:, 0] == numpy.amax(param_results[:, 0]))  # Maximum des R2

            best_out = model_energy_demand(wz_out, float(param_results[index, 1]), float(param_results[index, 2]),
                                           float(param_results[index, 3]), dfAnwend, True, True, 0.25)
            print(param_results[index])
            bestParams[wz_out] = param_results[index][0]

        if doOptimize is False:
            """
            Falls keine Optimierung stattfindet, werden die Default-Werte der Hyperparameter verwendet
            """
            param_results = [defaultFactSia, defaultFactDin, defaultFactGS[wz_out]]
            best_out = model_energy_demand(wz_out, param_results[0], param_results[1],
                                           param_results[2], dfAnwend, True, True, 0.25)
            bestParams[wz_out] = numpy.array(param_results)
        if doOutput is True:

            wz_out_str = str(wz_out)
            flname = outpath + wz_out_str
            if ownAssumptions:
                flname = flname + str("_Annahmen")

            if doOptimize:
                flname = flname + str("_Opti")
            if ownAssumptions is False and doOptimize is False:
                flname = flname + str("_TrueBottomUp")
            score_err_str = str(int(best_out["R2"][0]*100))
            flname = flname + str("_R" + str(score_err_str) + ".xlsx")
            writer = pd.ExcelWriter(flname, engine='xlsxwriter')
            best_out.to_excel(writer, sheet_name='Sheet1')
            if ownAssumptions:
                paramDF = pd.DataFrame(data=param_results)
                paramDF.to_excel(writer, sheet_name='Sheet2')
            workbook = writer.book
            workbook.close()
    syntheseworking = False


# In[Main: Szenario-Nachfrageflexi]

"""
Hauptmethode für das zweite und dritte Modul der Arbeit: Fortschreibung der Lastprofile und
Quantiizierung des Nachfrageflexibilisierungspotenzials.

Fügt dem Ausgabeordner des ersten Moduls die Dateien je Szenario mit entsprechendem Namen hinzu.
"""

if not firstRun:
    while syntheseworking:
        time.sleep(10)
    else:
        dsm_qst = ['Lüftung (Mechanische Energie)', 'Klimakälte',
                   'Prozesskälte', 'Raumwärme und Warmwasser']
        vent_jahr = numpy.tile(ventilation.copy(), 365)
        for wz_out_scen in [6471, 55, 86, 85, 47]:
            if doOptimize:
                ref_scen = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][1], bestParams[wz_out_scen][2],    
                                               bestParams[wz_out_scen][3], dfRefSzen, True, False, 0.58)
                bas_scen = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][1], bestParams[wz_out_scen][2],
                                               bestParams[wz_out_scen][3], dfBasSzen, True, False, 0.57)
                status_quo = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][1], bestParams[wz_out_scen][2],
                                               bestParams[wz_out_scen][3], dfAnwend, True, False, 0.57)
                
                # Siehe Anteile der Wärmepumpe an Raumwärme 2035 in Szenarien: St.: 58%, Norm.: 57%, Expl: 57%
            if doOptimize is False:
                ref_scen = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][0], bestParams[wz_out_scen][1],
                                               bestParams[wz_out_scen][2], dfRefSzen, True, False, 0.58)
                bas_scen = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][0], bestParams[wz_out_scen][1],
                                               bestParams[wz_out_scen][2], dfBasSzen, True, False, 0.57)
                status_quo = model_energy_demand(wz_out_scen, bestParams[wz_out_scen][0], bestParams[wz_out_scen][1],
                                               bestParams[wz_out_scen][2], dfAnwend, True, False, 0.57)
            ref_scen['Lüftung (Mechanische Energie)'] = ref_scen['Mechanische Energie']*vent_jahr*0.24
            bas_scen['Lüftung (Mechanische Energie)'] = bas_scen['Mechanische Energie']*vent_jahr*0.24
            status_quo['Lüftung (Mechanische Energie)'] = status_quo['Mechanische Energie']*vent_jahr*0.24
            for sp in dsm_qst:
                for scen in [ref_scen, bas_scen, status_quo]: # expl_scen]:
                    scen[sp + "_Pmax"], scen[sp + "_Pmin"] = dsm_p(scen[sp].copy().to_numpy(), 1)

                    if (sp == 'Lüftung (Mechanische Energie)' or sp == 'Klimakälte' or
                            sp == 'Prozesskälte'):  # Hier wird eine Verschiebedauer deltaT = 1h verwendet
                        scen[sp + "_Emax"], scen[sp + "_Emin"] = dsm_e(scen[sp].copy().to_numpy(), 1)
                    if sp == 'Raumwärme und Warmwasser':    # Hier wird eine Verschiebedauer deltaT = 12h verwendet
                        scen[sp + "_Emax"], scen[sp + "_Emin"] = dsm_e(scen[sp].copy().to_numpy(), 12)

            ref_scen_flname = outpath + "ReferenzstandsSzenario_" + str(wz_out_scen) + ".xlsx"
            bas_scen_flname = outpath + "BasisSzenario_" + str(wz_out_scen) + ".xlsx"
            status_quo_flname = outpath + "StatusquoSzenario_" + str(wz_out_scen) + ".xlsx"   
            refwriter = pd.ExcelWriter(ref_scen_flname, engine='xlsxwriter')
            baswriter = pd.ExcelWriter(bas_scen_flname, engine='xlsxwriter')
            statusquowriter = pd.ExcelWriter(status_quo_flname, engine='xlsxwriter')
            ref_scen.to_excel(refwriter, sheet_name="Sheet1")
            bas_scen.to_excel(baswriter, sheet_name="Sheet1")
            status_quo.to_excel(statusquowriter, sheet_name="Sheet1")
            workbook1 = refwriter.book
            workbook2 = baswriter.book
            workbook3 = statusquowriter.book
            workbook1.close()
            workbook2.close()
            workbook3.close()

# In[FirstRun = False]
firstRun = False
