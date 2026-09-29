# Praktikum Lehrkonzept

!!! info "Diese Seite ist auch auf Englisch verfügbar"
    [Sprache wechseln :gb:](teaching_english.md){ .md-button }

## Grundlegendes

### Über dieses Dokument

Dieses Dokument beschreibt ein in der universitären Lehre praktisch
erarbeitetes Lehrkonzept. Dieses hat das Ziel, Lehrende dabei zu
unterstützen, das `algobattle`-tool sowie dazugehörige Software für
die eigene Lehre einzusetzen. Der Fokus liegt hierbei auf dem
Lehraspekt. Für eine Erklärung der technischen Vorraussetzungen sowie
Bedienungdetails, konsultieren Sie bitte die [technische
Dokumentation](https://algobattle.org/docs).

## Für wen ist diese Software?

Das `algobattle`-Tool wurde seit 2019 am Lehr- und Forschungsgebiet Theoretische Informatik der RWTH Aachen University
entwickelt und für den Einsatz im Rahmen eines Softwarepraktikums für
Studierende des Bachelor Informatik entworfen. Obwohl die [Sammlung der von uns bereitgestellten Aufgaben](https://github.com/Algorithmic-Battle/algobattle-problems)
dies stark widerspiegelt, spricht nichts dagegen, das Tool für andere
Studiengänge oder sogar für den Schulunterricht in der Oberstufe
einzusetzen.

Das Projekt richtet sich damit an Lehrende, denen wir es durch unsere
Arbeit erleichtern möchten, eine kompetitive Lernerfahrung aufzubauen.
Die extrem modulare Natur des Projekts erlaubt es, über ein Semester
entweder viele verschiedene Themen abzudecken oder sich mit
ausgewählten Themen intensiv zu befassen.

## Muss ich Lizenzen bei der Verwendung beachten?

Die ganze Software wie auch die dazugehörigen Dokumente sind unter einer freien
MIT-Lizenz veröffentlicht, sofern nicht explizit anders angegeben. Sie
müssen daher kein Einverständnis einholen, um die Software und die
dazughörigen Dokumente und Veröffentlichungen zu verwenden, zu
modifizieren, weiterzuentwickeln oder in einem kommerziellen Rahmen
(z.B. in privaten Lehrstätten) zu verwenden. Wir fänden es jedoch
nett, wenn Sie dabei auf uns als Quelle verweisen würden.

## Für welche Teilnehmerzahl ist das Praktikum geeignet?

Wir empfehlen, die Studierenden in mehrere Einzelgruppen einzuteilen;
unserer Erfahrung nach ist eine Gruppengröße von sechs Personen am
besten geeignet. Von diesen kann es dann prinzipiell beliebig viele
geben. Dabei ist natürlich zu beachten, dass mit mehr Gruppen der
Betreuungsaufwand steigt. Wir konnten mit zwei Lehrenden den
Praktikumsbetrieb für 18 Studierende gut neben den sonstigen
beruflichen Tätigkeiten managen. Der effektive Zeitaufwand betrug dann
nicht mehr als zwei Wochentage.

## Aufbau

### Grundidee

Das Algorithmic Battle hat in seiner ursprünglichen Gestaltung als
Ziel, Studierenden eine praktische Auseinandersetzung mit sonst
theoretischem Vorlesungsstoff zu bieten. Im Informatikstudium ist die
Komplexitätstheorie ein wichtiger Baustein: Sie besagt, dass wir für
viele Probleme nicht erwarten dürfen, schnelle, korrekte und
allgemeingültige Algorithmen finden zu können.

Dabei wird oft vernachlässigt, dass diese schweren Probleme in der
Praxis dennoch gelöst werden müssen und tatsächlich auch gelöst
werden. Gerade durch den Boom von sogenannten MIP-Solvern wie Gurobi,
CPLEX und Konsorten werden praktische Optimierungsprobleme teilweise
rasend schnell gelöst.

Dies liegt darin begründet, dass ein Problem als Sammlung von allen
möglichen Instanzen zwar schwer beherrschbar ist, mitunter aber viele
Teilmengen dieser Instanzen trotzdem sehr schnell korrekt lösbar sind,
wie es bei praktischen Instanzen oft der Fall zu sein scheint.

### Lernziele

Der Fokus des Praktikums liegt daher darin, Studierende beide
Perspektiven des Lösungsprozesses einnehmen zu lassen. Sie sollen im
Kern zwei Fragen beantworten:

- Was sind "schwere Instanzen" eines Problems?
- Wie schreibe ich Algorithmen, die in den meisten Fällen schnell und korrekt sind?

Dies bedeutet, dass die Studierenden sowohl einen `generator` für die
Erstellung schwerer Instanzen (für eine gegebene Instanzgröße)
schreiben müssen, als auch einen `solver`, der eine Instanz
entgegennimmt und innerhalb eines Zeitlimits eine möglichst gute
Lösung ausgibt.

Jeder `generator` eines Teams läuft dann gegen jeden `solver` eines
Teams. Im klassischen Setting ist dann die Frage, bis zu welcher
Instanzgröße der Solver des einen Teams noch die Instanzen des anderen
Teams lösen kann. Bewertet wird dann, _wie viel besser_ die
Studierenden sind: Die höchste noch gelöste Instanzgröße zählt und
wird mit der höchsten noch gelösten Instanzgröße des anderen Teams
verglichen und entsprechend Punkte vergeben. Um diesen relativen
Abstand zu maximieren, ist es also wichtig, dass einerseits der eigene
`generator` stark ist, damit das gegnerische Team nicht sehr weit mit
ihrem `solver` kommen. Es ist aber genauso wichtig, dass der eigene
`solver` stark ist, um überhaupt die Instanzen des anderen Teams
möglichst lange lösen zu können.

Besonders attraktiv für den Lernprozess ist hierbei, dass wir
keinerlei Einschränkungen vorgeben, welche externe Software die
Studierenden für das Erreichen dieser Ziele verwenden (solange es
keine lizenzrechtlichen Probleme o.Ä. gibt). Da alle Software in
Dockercontainern läuft und man sich auch im echten Leben nicht
künstlich geißelt, sind die Studierenden angehalten, möglichst breit
zu recherchieren, um Publikationen, Beschreibungen von Algorithmen oder
direkt ganze Tools oder Libraries zu finden und zu verwenden. Es gibt
lediglich folgende Einschränkungen, die wir forcieren:

- Nur Software verwenden, deren Lizenz es erlaubt.
- Kein Ausspähen oder Absprechen zwischen den Teams.
- Keine Exploits unserer Software ausnutzen (siehe auch [Bug Bounties](#bug-bounties)).

Den Code für beides ließen wir die Studierenden in einem für uns
Betreuer einsehbaren Versionsverwaltungssystem (in unserem Fall
gitlab) entwickeln. Damit müssen sich die Studierenden als
Softwareteam koordinieren und organisieren, sei es über einfache
Absprachen, Issues oder aggressives Branching mit anschließenden Pull
Requests. Außerdem lässt sich bereits während des Praktikums gut
feststellen, ob Einzelpersonen nur unzureichende Beiträge liefern und man
entsprechend frühzeitig gegensteuern muss.

Darüber hinaus ist der gesamte Entwicklungsprozess zu dokumentieren.
Jeder recherchierte Ansatz, jede Implementation einer Idee, egal ob
geglückt oder nicht, ist festzuhalten. Dazu haben wir sehr erfolgreich
das Prinzip verfolgt, dass jede Person einmal im Semester für die
Dokumentation verantwortlich ist. Die anderen Personen müssen dann
dieser Person eigenständig zutragen, was sie gemacht haben. Die
dokumentierende Person ist also nicht verantwortlich für das Einholen
von Informationen. Im Gegenteil: Wer nichts meldet, der steht am Ende
nicht in der Dokumentation und hat damit - so müssen die Betreuenden es annehmen -
auch nichts getan.

### Beispiel für den Aufbau eines Semesters

Wir beschreiben im Folgenden den Aufbau eines typischen
Universitätssemesters an der RWTH Aachen University. Dieser Aufbau ist
selbstverständlich nicht bindend und stellt ein Format dar, welches
wir seit mehreren Jahren mit sehr positiver Rückmeldung der
Studierenden durchführen.

In Bezug auf unser Praktikum beginnt jedes Semester bei uns gleich. Kurz vor bzw. zu Beginn der
Vorlesungszeit veranstalten wir ein Kickofftreffen, in dem wir die
Studierenden über das Format und den Aufbau des Praktikums
informieren. Anschließend finden wir gemeinsam einen regelmäßigen
Wochentermin und teilen die Studierenden in 6er-Gruppen auf. Dabei
achten wir stark darauf, dass sich in diesen Gruppen maximal 3
Personen bereits kennen, um möglichen Ausgrenzungen entgegenzuwirken.

Die erste Aufgabe ist stets dieselbe, wir verwenden die
`pairsum`-Aufgabe aus dem `algobattle-problems`-Repository; die
dort erreichten Punkte fließen noch nicht in die Gesamtwertung. Diese
Aufgabe dient dazu, sich mit einer Entwicklungsumgebung, unserer
Software und dem Format der Battles vertraut zu machen. Eine
Dokumentation muss hier allerdings bereits erstellt werden. Der Ablauf entspricht dem
aller künftigen Aufgaben: Wir fangen nach einer Woche an, täglich
ein Battle mit dem aktuellen Stand der Software der Studierenden
durchzuführen. So wird regelmäßig reflektiert, wie gut oder
schlecht sich der eigene Code gegenüber dem der anderen Gruppen
schlägt.

An das Ende dieser Aufgabe sowie an das Ende jeder folgenden Aufgabe
schließt sich ein Abschlusstreffen an. In diesem verlangen wir von
zwei in diesem Meeting ausgewürfelten Personen, dass sie die zentralen
Ideen ihrer `solver` und `generator` dem Rest der Studierenden
vorstellen. Wir erwarten, dass jede Person über die Software und den
Fortschritt wie über die Bearbeitungszeit informiert sind, was wir durch
die zufällige Auswahl der Vortragenden zu forcieren versuchen.

Anschließend stellen wir die Gesamtergebnisse der Battles vor,
besprechen mögliche Bug Bounties und diskutieren in einer offenen
Runde, was die Studierenden gelernt haben. Zum Schluss wird der Inhalt
der nächsten Aufgabe vorgestellt.

Der Bearbeitungszyklus ist dann immer gleich: Nach Erhalt der
Aufgabenbeschreibung lassen wir die Gruppen für eine Woche lang
recherchieren und implementieren. Nach dieser Woche treffen wir uns
mit jeder Gruppe separat. Darin besprechen wir die gefundenen Ansätze,
Ideen und Probleme, die sich eventuell bereits zu diesem Zeitpunkt
zeigen. Nach diesem Treffen starten nächtliche Battles, wobei das
erste dieser Battles unbewertet ist, um noch mögliche Softwarebugs
auszumerzen. Danach sind alle Battles bepunktet, bis zum nächsten
Abschlusstreffen.

In einem typischen Semester ist somit Zeit für 6-7 Aufgaben nach
diesem Format (die `pairsum`-Aufgabe bereits eingerechnet). Wir
empfehlen sehr, bei 6 Aufgaben zu bleiben und die freiwerdenen Wochen
als Puffer für andere Aufgaben zu verwenden. Einerseits reduziert sich
so der Arbeitsdruck für die Studierenden etwas, andererseits deckt
sich dann die Anzahl der anzufertigenden Dokumentationen mit den
Gruppengrößen.

Bezüglich des Lernziels der einzelnen Aufgaben arbeiten wir momentan
nach grob nach folgendem Schema:

0. `pairsum` zum Aufwärmen.
1. Klassisches NP-vollständiges Problem um Recherche attraktiv zu machen.
2. Problem in P für starke Optimierungen von Datenstrukturen und Algorithmen.
3. Approximationsproblem mit Approximationsrate, die nicht polynomiell erreichbar ist (z.B. 1.5 an Vertex Cover).
4. Nicht-klassisches NP-vollständiges Problem, um MIP-Solver attraktiv zu machen.
5. Wildcard, z.B. Problem mit stark beschränktem Speicher, Problem in FPT, ...

Nach der sechsten Aufgabe endet das Praktikum bei uns mit der
Vorlesungszeit. Anschließend folgt die Bewertung und Notengebung.

## Bewertung der Studierenden

Falls man die Teilnehmer des Praktikums am Ende benoten möchte, geben
wir hiermit noch ein paar Anregungen, worauf diese Bewertung
basieren könnte. Wir prüfen die folgenden Punkte meist schon einmal in
der Mitte des Semesters, um Einzelpersonen zu unterstützen, welche in unseren Augen
abgehängt wurden.

### Qualität der Software

Durch die Qualität der von den Studierenden erstellten Software ergibt sich
ein Voreindruck für die Notengebung. Die zentrale Frage hier lautet:
Wie viel Aufwand ist in die Erarbeitung der Software über das Semester
hinweg geflossen? Eine Gruppe, die zwar viele Battles verliert, dabei
aber viele verschiedene Ansätze recherchiert und ausprobiert hat,
ist unserer Meinung nach nicht schlecht zu bewerten, nur weil die
Ergebnisse in den Battles nicht sehr gut sind.

### Dokumentation

Hier ist die für die Dokumentation zuständige Person natürlich davon
abhängig, was und in welcher Qualität die anderen Gruppenmitglieder
ihr über die eigene Arbeit berichtet haben. Daher kann man anhand der Dokumentation
sehen, welche Gruppenmitglieder in welchen Wochen Arbeit geleistet
haben. Wir werten Personen ab, welche über das ganze Semester hinweg
nur eine Art von Arbeit geleistet haben, z.B. nur implementiert oder
nur recherchiert haben.

### Vorträge

Falls eine Person offensichtlich unvorbereitet ist, führt dies zur Abwertung.
Anhand der Vorträge lässt sich auch recht gut feststellen, ob die Vortragenden
wissen, was in der Gruppenarbeit geleistet wurde.

### Implementationsarbeit

Da es sich um ein Softwareprojektpraktikum handelt, lassen wir niemanden
bestehen, der nicht an Implementierungsarbeit beteiligt war, sei es
durch Pair Programming oder eigenständige Implementationen. Dies lässt
sich am einfachsten über die Commit History der Gruppe feststellen.

## Weitere Anwendungsmöglichkeiten der Software

Wir möchten an dieser Stelle betonen, dass wir das `algobattle`-Tool
bewusst sehr modular geschrieben haben, was die Art der Aufgaben und
die eigentliche Durchführung der Battles betrifft. Während wir als
Autoren einen sehr theoriegeprägten Hintergrund haben und uns daher
hauptsächlich für Probleme interessieren, welche der Theorie
nahestehen, spricht nichts dagegen, andere Typen von Aufgaben und
Battles durchzuführen.

### Andere Arten von Battles

Wir sind in der bisherigen Beschreibung davon ausgegangen,
dass ein Battle immer so durchgeführt wird, dass sich `generator` und
`solver` zu immer größeren Instanzgrößen duellieren. Die
Bepunktung ist dann davon abhängig, wie groß der relative Unterschied
zwischen den größten noch gelösten Instanzen ist. Dies ist allerdings
nur die Beschreibung eines `battle type`s, dem `iterated`-type.

Ein von uns mitgelieferter, alternativer `battle type` ist der
`averaged`-type, in dem nur Instanzen der gleichen Instanzgröße über
eine Anzahl an Wiederholungen hinweg zu lösen sind. Die Bewertung
erfolgt dann über die durchschnittliche Lösungsqualität eines Solvers.

Prinzipiell lassen sich alle Arten von Abstraktionen einzelner
Fights zwischen `generator` und `solver` implementieren.

### Andere Arten von Aufgaben

In den meisten unserer
[Beispielaufgaben](https://github.com/Algorithmic-Battle/algobattle-problems)
sind Input und Output von `generator` und `solver` einfache
json-Dateien, welche Text enthalten. Da die Schnittstelle allerdings
beliebige Dateien- und Ordnerstrukturen zulässt, spricht nichts
dagegen, etwa Multimediainhalte wie Musik oder Bilder als Ein- und
Ausgaben der `generator` und `solver` zu spezifizieren.

## Sonstiges

### Bug Bounties

Wir ermutigen unsere Studierenden, sowohl unser
`algobattle`-Framework als auch die von uns geschriebenen Aufgaben
möglichst kaputtzumachen. Konkret interessieren wir uns für
Eingaben, mit denen Studierende in der Lage sind, unseren Code zu crashen,
die `solver` bzw. `generator` der anderen Teams zu crashen oder
auszunutzen, bis hin zu Möglichkeiten, über das Ausführen der Battles
an die docker-images der anderen Teams zu gelangen. Wie bereits
erwähnt, verlangen wir, dass diese Exploits nicht während regulärer
Battles genutzt werden, um eine bessere Punktzahl zu erreichen. Dafür
belohnen wir das Auffinden solcher Bugs mit Bonuspunkten: Die erste
Gruppe, die uns auf einen reproduzierbaren Fehler hinweist, erhält
zusätzliche Punkte in Abhängigkeit davon, wie gravierend der Fehler
ist.

Der große Vorteil dieses Verfahrens ist, dass wir die natürliche
Neugier, Systeme zu erkunden, gesteuert belohnen können und wir weitere
Testcases für unseren eigenen Code erhalten. Gleichzeitig können wir
die Bemühungen der Studierenden belohnen.

### Bekannte Fallstricke

Unserer Erfahrung nach stellen Studierende irgendwann fest, dass
MIP-Solver existieren. Diese sind für viele Aufgabenstellungen Gift,
da sich diese schnell einschleifen und als Allzweckwaffe genutzt
werden. Wir empfehlen daher grundsätzlich, den Aufgabenpool so zu
gestalten, dass das wiederholte Verwenden der gleichen Software
unattraktiv wird. Im Falle von MIP-Solvern hilft es bereits, den
verfügbaren Arbeitsspeicher einzuschränken, da diese meist sehr
speicherintensiv arbeiten.

### Weitere Ressourcen

[Das Algobattle-Framework (Github)](https://github.com/Algorithmic-Battle/algobattle)  
[Sammlung von Problemen für Algobattle (Github)](https://github.com/Algorithmic-Battle/algobattle-problems)  
[Webframework für Algobattle (Github)](https://github.com/Algorithmic-Battle/algobattle-web)  
[Technische Dokumentation](https://algobattle.org/docs)
