## Pinnanseurantapalvelu
Palvelin, joka sisältää 1. tietokannan, 2. REST API:n vastaanottamaan IoT-mittalaitteiden dataa, sekä 3. Graafisen käyttöliittymän

**Huom! Keskeneräinen!**

### To-do:
1. Kirjoita ohjeet käyttöön..
2. api:
    * Refaktoroi ilmoituslogiikka siistimmäksi (alert_logic.py)
    * lisää päätepisteitä dashboardia varten
    * lisää skeemoja, oikea validointi
    * autentikointi
3. dashboard:
    * Parempi visualisointi, kun laitteita on paljon
    * Korjaa nappien toiminta
    * Käytä kevyempää kirjastoa ja korjaa vibe-koodattu dashboard (eli tee kokonaan uusi)
4. tietokanta
    * Laitteiden asetus aktiiviseksi/inaktiiviseksi? ym.
5. Docker
    * Ota selvää kuvien optimoinnista
