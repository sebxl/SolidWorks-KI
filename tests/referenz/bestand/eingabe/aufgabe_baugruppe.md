# Revision Hubeinheit (Referenz Paket Bestandsdateien, Etappe 2)

Die Baugruppe `Hubeinheit.SLDASM` stammt von einem Kollegen: Grundplatte, Schlitten auf einer Grenzverknüpfung `Hub` (0 bis 25 mm), zwei
Anschläge aus derselben Datei, Unterbaugruppe `Muster` mit dem importierten Motor, Konfigurationen Standard und „Ohne Antrieb“. Beim
Durchsehen sind diese Punkte aufgefallen. Alles andere bleibt, wie es ist.

1. Die Grundplatte wird 18 statt 15 mm dick. Sie wächst nach oben, Schlitten und Anschläge wandern mit.
2. Der Schlitten wird 10 mm länger, 70 statt 60, nach +X. Die Länge hängt an der globalen Variable `L` im Teil.
3. In das Kernloch auf der Oberseite des Schlittens kommt eine Klemmschraube ISO 4762 M6×16. Der Kopf liegt auf der Oberseite auf. Das
   Gewinde ist nicht modelliert, die Überlappung mit dem Kernloch ist gewollt.
4. Der Hub geht bis 30 statt 25 mm.
5. Der zweite Anschlag entfällt samt seinen Verknüpfungen.
6. Der erste Anschlag wird durch den höheren neuen ersetzt (`anschlag_neu.yaml`, 40 statt 30 mm), er sitzt an derselben Stelle.

Die Unterbaugruppe `Muster`, der Motor und die Lage aller nicht genannten Komponenten ändern sich nicht. Die Baugruppe muss danach
nachweislich noch fahren.
