"""Controls virtual machines through libvirt"""
import logging
from lnxlink.modules.scripts.helpers import import_install_package

logger = logging.getLogger("lnxlink")


class Addon:
    """Addon module"""

    def __init__(self, lnxlink):
        """Setup addon"""
        self.name = "Linklibvirt"
        self.lnxlink = lnxlink
        self._requirements()
        try:
            self.conn = self.libvirt.open('qemu:///system')
            logger.info("Connected to libvirt")
        except Exception as err:
            logger.error("Failed to connect to libvirt: %s", err)
            raise SystemError("Failed to connect to libvirt") from err
        self.domains = {}

    def _requirements(self):
        """Import required packages"""
        self.libvirt = import_install_package("libvirt-python", ">=11.1.0", "libvirt")

    def _get_domain_by_name(self, name):
        """Get domain by name with case-insensitive matching"""
        try:
            # First try exact match
            return self.conn.lookupByName(name)
        except self.libvirt.libvirtError:
            # If exact match fails, try case-insensitive match
            domains = self.conn.listAllDomains()
            for domain in domains:
                if domain.name().lower() == name.lower():
                    return domain
            raise self.libvirt.libvirtError(f"Domain '{name}' not found")
        except Exception as err:
            logger.error("Error looking up domain %s: %s", name, err)
            raise

    def get_info(self):
        """Gather information from the system"""
        try:
            domains = self.conn.listAllDomains()
            for domain in domains:
                try:
                    state, _ = domain.state()
                    state_str = "OFF"
                    if state in [self.libvirt.VIR_DOMAIN_RUNNING, self.libvirt.VIR_DOMAIN_PAUSED]:
                        state_str = "ON"
                    
                    self.domains[domain.name()] = {
                        "state": state_str,
                    }
                except Exception as err:
                    logger.error("Failed to get info for domain %s: %s", domain.name(), err)
                    continue
        except Exception as err:
            logger.error("Failed to get domain list: %s", err)
        logger.info(self.domains)
        return self.domains

    def start_control(self, topic, data):
        """Control system"""
        try:
            domain_name = topic[1].replace("libvirt_", "")
            domain = self._get_domain_by_name(domain_name)
            state, _ = domain.state()
            
            if data.upper() == "ON":
                if state == self.libvirt.VIR_DOMAIN_RUNNING:
                    logger.info("Domain %s is already running", domain_name)
                else:
                    logger.info("Starting domain %s", domain_name)
                    domain.create()
            elif data.upper() == "OFF":
                if state == self.libvirt.VIR_DOMAIN_SHUTOFF:
                    logger.info("Domain %s is already stopped", domain_name)
                else:
                    logger.info("Stopping domain %s", domain_name)
                    domain.destroy()
        except Exception as err:
            logger.error("Failed to control domain %s: %s", domain_name, err)

    def exposed_controls(self):
        """Exposes to home assistant"""
        controls = {}
        try:
            domains = self.conn.listAllDomains()
            for domain in domains:
                try:
                    name = domain.name()
                    controls[f"libvirt_{name}"] = {
                        "type": "switch",
                        "icon": "mdi:server",
                        "command_topic": f"libvirt/{name}/command",
                        "state_on": "ON",
                        "state_off": "OFF",
                        "value_template": f"{{{{ value_json.get('{name}', {{}}).get('state') }}}}",
                    }
                except Exception as err:
                    logger.error("Failed to get control info for domain %s: %s", domain.name(), err)
                    continue
        except Exception as err:
            logger.error("Failed to get domain list: %s", err)
        return controls
