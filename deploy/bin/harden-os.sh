#!/bin/bash
# =============================================================================
# OS-level hardening for Vivify Ecosystem VPS
# CIS-inspired: UFW, SSH, kernel parameters, fail2ban, automatic updates
# Run as root once on a fresh VPS.
# =============================================================================
set -euo pipefail

echo "🔒 Harden-OS: Starting VPS security hardening..."

# ── 1. UFW Firewall (default deny, whitelist only) ──
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

# ── 2. SSH hardening ──
sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/^#ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config
sed -i 's/^#ClientAliveCountMax.*/ClientAliveCountMax 0/' /etc/ssh/sshd_config
sed -i 's/^#AllowUsers.*/AllowUsers deploy/' /etc/ssh/sshd_config
systemctl reload sshd

# ── 3. Automatic security updates ──
apt-get install -y unattended-upgrades apt-listchanges
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF
cat > /etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
systemctl restart unattended-upgrades

# ── 4. Kernel parameters (sysctl) ──
cat >> /etc/sysctl.d/99-hardening.conf <<'EOF'
# IP spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
# Ignore source-routed packets
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
# Disable ICMP redirect sending
net.ipv4.conf.all.send_redirects = 0
# Enable TCP SYN cookies (prevents SYN flood)
net.ipv4.tcp_syncookies = 1
# Enable proper reverse path filtering
net.ipv4.conf.all.rp_filter = 1
# Disable martian packets
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
EOF
sysctl --system

# ── 5. Fail2Ban (SSH + Nginx) ──
apt-get install -y fail2ban
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = %(sshd_log)s

[nginx-http-auth]
enabled = true
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
logpath = /var/log/nginx/access.log
maxretry = 10
EOF
systemctl restart fail2ban

# ── 6. File permissions ──
chmod 750 /var/www/vivify
chmod 640 /var/www/vivify/shared/.env
chown -R www-data:www-data /var/www/vivify
chmod 700 /var/www/vivify/deploy/bin/*.sh
chmod 700 /var/www/vivify/deploy/bin/*-vivify
chmod 700 /var/www/vivify/deploy/bin/*-start

# ── 7. Disable unused filesystems (mitigate kernel exploits) ──
cat > /etc/modprobe.d/disable-fs.conf <<'EOF'
install cramfs /bin/true
install freevxfs /bin/true
install jffs2 /bin/true
install hfs /bin/true
install hfsplus /bin/true
install squashfs /bin/true
install udf /bin/true
install vfat /bin/true
EOF

# ── 8. Check Nginx version for CVE-2026-42945 ──
NGINX_VER=$(nginx -v 2>&1 | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1)
if dpkg --compare-versions "$NGINX_VER" lt "1.30.1"; then
  echo "⚠️  WARNING: Nginx $NGINX_VER is vulnerable to CVE-2026-42945 (rewrite module heap overflow)"
  echo "   Upgrade to ≥1.30.1: add the official Nginx repo or use nginx-extras"
fi

echo "✅ Harden-OS concluído. Reinicie o servidor para aplicar todas as mudanças."
