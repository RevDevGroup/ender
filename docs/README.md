# SMS Gateway con MQTT y Celery

Esta es una implementación de un gateway SMS que utiliza MQTT para la comunicación con dispositivos y Celery para el procesamiento asíncrono de mensajes, eliminando la dependencia de direcciones IP.

## Arquitectura

### Diagrama de Arquitectura

```
[Dispositivos] <---MQTT (TLS)---> [Broker Mosquitto] <---MQTT---> [Servidor FastAPI]
                                      |                                      |
                                      |                                      |
                                      v                                      v
                               [Autenticación API Key]               [Celery Workers]
                                      |                                      |
                                      v                                      v
                               [Base de Datos]                      [Envío de SMS]
```

### Componentes

1. **Dispositivos**: Conectados via MQTT usando API Keys únicas.
2. **Broker MQTT**: Mosquitto con autenticación y TLS.
3. **Servidor Central**: FastAPI manejando conexiones y API.
4. **Celery**: Procesamiento asíncrono de tareas.
5. **Base de Datos**: PostgreSQL para usuarios, mensajes, dispositivos y API keys.

## Instalación y Configuración

### Prerrequisitos

- Python 3.10+
- Docker y Docker Compose
- PostgreSQL
- RabbitMQ

### Configuración del Entorno

1. Clona el repositorio y activa el entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configura las variables de entorno en `.env`:
   ```
   DATABASE_URL=postgres://user:pass@localhost:5432/db
   API_SECRET_KEY=your-secret-key
   BROKER_URL=amqp://user:pass@localhost:5672//
   RESULT_BACKEND=redis://localhost:6379/0
   RATE_LIMIT=10/m

   MQTT_BROKER_HOST=localhost
   MQTT_BROKER_PORT=8883
   MQTT_USERNAME=admin
   MQTT_PASSWORD=password
   MQTT_TLS_CERT=path/to/cert.pem
   MQTT_TLS_KEY=path/to/key.pem
   MQTT_CA_CERT=path/to/ca.pem
   ```

3. Inicia los servicios con Docker Compose:
   ```bash
   docker-compose -f docker-compose-dev.yml up -d
   ```

4. Genera certificados TLS para MQTT (opcional pero recomendado):
   ```bash
   openssl req -new -x509 -days 365 -extensions v3_ca -keyout mosquitto/config/ca.key -out mosquitto/config/ca.crt
   openssl genrsa -out mosquitto/config/server.key 2048
   openssl req -out mosquitto/config/server.csr -key mosquitto/config/server.key -new
   openssl x509 -req -in mosquitto/config/server.csr -CA mosquitto/config/ca.crt -CAkey mosquitto/config/ca.key -CAcreateserial -out mosquitto/config/server.crt -days 365
   ```

5. Configura usuarios en Mosquitto:
   ```bash
   mosquitto_passwd -c mosquitto/config/passwords admin
   ```

### Ejecutar la Aplicación

1. Ejecuta las migraciones de la base de datos:
   ```bash
   python main.py
   ```

2. Inicia los workers de Celery:
   ```bash
   celery -A app.worker.celery_app worker --loglevel=info
   ```

3. La API estará disponible en `http://localhost:8000`.

## Guía de Implementación para Dispositivos

### Conexión MQTT

Los dispositivos deben conectarse al broker MQTT usando TLS y autenticación.

**Ejemplo en Python:**

```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.username_pw_set("admin", "password")
client.tls_set(ca_certs="ca.crt", certfile="client.crt", keyfile="client.key", tls_version=ssl.PROTOCOL_TLS)
client.connect("broker.example.com", 8883, 60)

# Autenticar con API Key
client.publish("devices/auth/YOUR_API_KEY", "client_id")

# Escuchar mensajes
client.subscribe("devices/YOUR_API_KEY/sms")
client.on_message = lambda client, userdata, msg: print(f"SMS: {msg.payload.decode()}")

client.loop_forever()
```

### Protocolo de Comunicación

- **Autenticación**: Publicar en `devices/auth/{api_key}` con el client_id.
- **Mensajes**: Recibir en `devices/{api_key}/sms` con formato `phone:message_body`.
- **Respuestas**: El servidor confirma en `server/auth/{api_key}`.

## API Endpoints

### Dispositivos

- `GET /devices`: Listar dispositivos.
- `POST /devices`: Crear dispositivo.
- `POST /devices/{id}/api-keys`: Generar API key.
- `GET /devices/{id}/api-keys`: Listar API keys.

### Mensajes

- `GET /messages`: Listar mensajes del usuario.
- `POST /messages/create`: Enviar mensaje.

## Seguridad

- Todas las comunicaciones MQTT usan TLS/SSL.
- API Keys únicas por dispositivo con expiración opcional.
- Rotación periódica de claves recomendada.
- Logging de accesos no autorizados.

## Pruebas

### Escalabilidad

- Conectar múltiples dispositivos simulados.
- Medir latencia y throughput.

### Tolerancia a Fallos

- Desconectar broker y verificar reconexión automática.
- Simular fallos de red.

### Rendimiento

- Enviar mensajes bajo carga pesada.
- Monitorear uso de CPU y memoria.

## Monitoreo

- Logs en `/mosquitto/log/mosquitto.log`.
- Métricas de Celery via Flower.
- Dashboard de RabbitMQ en `http://localhost:15672`.