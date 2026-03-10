#ifndef SMARTHOUSE_MQTT_CLIENT_H
#define SMARTHOUSE_MQTT_CLIENT_H

// Interface stub: MQTT transport contract for discovery/event/control flow.
int sh_mqtt_connect(void);
int sh_mqtt_publish_discovery(const char* payload_json);
int sh_mqtt_publish_event(const char* payload_json, int qos);
int sh_mqtt_publish_telemetry(const char* payload_json, int qos);
int sh_mqtt_publish_status(const char* payload_json, int qos);
int sh_mqtt_subscribe_control(void (*handler)(const char* payload_json));
int sh_mqtt_disconnect(void);

#endif
