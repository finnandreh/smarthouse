#ifndef SMARTHOUSE_DEVICE_IDENTITY_H
#define SMARTHOUSE_DEVICE_IDENTITY_H

// Interface stub: device identity and attestation contract.
typedef struct {
    const char* device_id;
    const char* house_id;
    const char* device_type;
    const char* protocol;
    const char* firmware_version;
} sh_device_identity_t;

int sh_identity_load(sh_device_identity_t* out_identity);
int sh_identity_validate(const sh_device_identity_t* identity);

#endif
