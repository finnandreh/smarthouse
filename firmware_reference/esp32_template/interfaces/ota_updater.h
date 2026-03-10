#ifndef SMARTHOUSE_OTA_UPDATER_H
#define SMARTHOUSE_OTA_UPDATER_H

// Interface stub: OTA lifecycle hooks.
int sh_ota_check_for_update(void);
int sh_ota_validate_package(const void* image, unsigned int image_size);
int sh_ota_apply_update(void);

#endif
