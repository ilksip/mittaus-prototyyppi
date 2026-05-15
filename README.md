## Pinnanseurantapalvelu
Järjestelmä, joka sisältää 1. tietokannan, 2. REST API:n vastaanottamaan IoT-mittalaitteiden dataa, sekä 3. Dashboard järjestelmän hallintaan

### Huomioita
- ⚠️ **Keskeneräinen/In progress!** ⚠️
- Testailen muutamia uusia asioita, ei välttämättä ollenkaan käytännöllinen

### Käyttöönotto (vielä tässä vaiheessa)
Vaatimukset:
* Internet-yhteys
* Git
* Docker ja Docker Compose

Askeleet:

1. Kloonaa repo ja siirry projektihakemistoon:

2. Luo `.env` tiedosto projektin juureen (`.env_example`):

```sh
# Docker vakioarvot, muuta kun tarpeen.
POSTGRES_USER=app_db
POSTGRES_PASSWORD=app_password
POSTGRES_DB=db
POSTGRES_HOST=db
POSTGRES_PORT=5432

MAIL_SERVICE_ENABLED=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASS=change-me

APP_TIMEZONE=Europe/Helsinki
DEBUG=false
LOG_TO_FILE=false
LOG_FILE_PATH=/app/logs/api.log
```

Sähköpostiasetuksia käytetään vasta, kun `MAIL_SERVICE_ENABLED=true`. Kehityskäytössä arvon voi pitää `false`, jolloin API kirjaa sähköpostit lokiin lähettämisen sijaan.

3. Rakenna ja käynnistä palvelut:

```sh
docker compose up --build
```

Taustalle käynnistys:

```sh
docker compose up --build -d
```

4. Avaa palvelut selaimessa:
* Dashboard: `http://localhost:8501`
* API: `http://localhost:5000/api`

5. Tarkista, että API vastaa:

```sh
curl http://localhost:5000/api/devices
```

6. Rekisteröi laite joko IoT-esimerkillä tai testipyynnöllä:

```sh
curl -X POST http://localhost:5000/api/registerDevice \
  -H "Content-Type: application/json" \
  -d '{"mac_address":"AA:BB:CC:DD:EE:FF"}'
```

Vastaus sisältää laitteen UUID:n. Lähetä testitelemetria tällä UUID:lla:

```sh
curl -X POST http://localhost:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "<device-uuid>",
    "sensor_values": {
      "fill_level": 50,
      "battery": 100
    }
  }'
```

7. Hallitse järjestelmää dashboardista:
* `Devices`: muuta laitteen nimeä, säiliön korkeutta, bufferia ja hälytysten päälläoloa.
* `Contacts`: lisää, muokkaa ja poista hälytyskontakteja.
* `Assignments`: määritä laitteen hälytyskontaktit.
* `Thresholds`: lisää, muokkaa ja poista laitteen hälytysrajat.
* `Telemetry`: hae ja näytä laitteen täyttöasteprosentti.

Hyödyllisiä komentoja:

```sh
docker compose logs -f api
docker compose logs -f dashboard
docker compose down
```

Tietokannan data säilyy Docker-volumessa `db_data` käynnistysten välillä. Jos haluat aloittaa täysin tyhjästä ja ajaa `db/init.sql` uudelleen, poista volyymi:

```sh
docker compose down -v
docker compose up --build
```

### To-do:
1. Api:
    * Järkevä datan validointi
    * Autentikoinnin lisääminen
2. Käyttöönotto
    * Jaettava Docker-kuva olisi hyvä
    * Toiminta kokonaan ilman Dockeria + asennusskripti tms.? 
3. Tietokanta
    * Ota selvää miten saada sopimaan olemassaoleviin tietokantoihin
4. Dashboard
    * Visualisoinnissa valinta sensorien välille
5. Testaus
    * Tee simulaatio-ohjelma, minkä kautta luoda ja generoida feikkidataa testaamiseen...