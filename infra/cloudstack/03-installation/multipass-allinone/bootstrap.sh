#!/usr/bin/env bash
# CloudStack 4.20 단일 노드 부트스트랩 — Apple Silicon Multipass Ubuntu 22.04 (ARM64) 기준
# 학습용. 프로덕션 금지.
#
# 사용:
#   $ multipass launch --cpus 8 --memory 12G --disk 80G --name cloudstack 22.04
#   $ multipass transfer bootstrap.sh cloudstack:/home/ubuntu/
#   $ multipass shell cloudstack
#   $ sudo bash bootstrap.sh
#
# 참고:
#   - 한 번에 다 도는 것보다 각 단계 수동 실행 후 트러블슈팅 권장
#   - 출처: https://docs.cloudstack.apache.org/en/latest/installguide/

set -euo pipefail

# ===== 설정값 =====
LANIP="${LANIP:-$(hostname -I | awk '{print $1}')}"
GATEWAY="${GATEWAY:-192.168.64.1}"
NETMASK_CIDR="${NETMASK_CIDR:-24}"
NIC="${NIC:-enp0s2}"
DB_ROOT_PASS="${DB_ROOT_PASS:-cloudstack}"
DB_CLOUD_PASS="${DB_CLOUD_PASS:-cloudstack}"
MGMT_KEY="${MGMT_KEY:-password}"
DB_KEY="${DB_KEY:-password}"
ARCH="${ARCH:-aarch64}"        # x86_64 환경이면 x86_64로 변경
SYSVM_URL="${SYSVM_URL:-http://download.cloudstack.org/systemvm/4.20/systemvmtemplate-4.20.0-${ARCH}-kvm.qcow2.bz2}"

echo "===== Vars ====="
echo "LANIP=$LANIP NIC=$NIC GATEWAY=$GATEWAY ARCH=$ARCH"
echo "================"

[[ $EUID -ne 0 ]] && { echo "Run as root (sudo bash $0)"; exit 1; }

# ===== 1. 패키지 =====
apt update
apt install -y vim net-tools bridge-utils chrony openssh-server curl gpg

systemctl enable --now chrony

# ===== 2. cloudbr0 브리지 =====
# 이미 있으면 skip
if ! ip link show cloudbr0 &>/dev/null; then
cat > /etc/netplan/50-cloud-init.yaml <<EOF
network:
  version: 2
  ethernets:
    ${NIC}:
      dhcp4: false
      dhcp6: false
  bridges:
    cloudbr0:
      addresses: [${LANIP}/${NETMASK_CIDR}]
      gateway4: ${GATEWAY}
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
      interfaces: [${NIC}]
      parameters:
        stp: false
        forward-delay: 0
EOF
chmod 600 /etc/netplan/50-cloud-init.yaml
netplan generate
netplan apply
sleep 5
fi

# ===== 3. NFS =====
apt install -y nfs-kernel-server nfs-common
mkdir -p /export/{primary,secondary} /mnt/{primary,secondary}
chmod 777 /export/primary /export/secondary

grep -q "/export/primary" /etc/exports || cat >> /etc/exports <<EOF
/export/primary *(rw,async,no_root_squash,no_subtree_check)
/export/secondary *(rw,async,no_root_squash,no_subtree_check)
EOF

systemctl enable --now nfs-kernel-server
exportfs -a

grep -q ":/export/primary" /etc/fstab || cat >> /etc/fstab <<EOF
${LANIP}:/export/primary   /mnt/primary   nfs defaults 0 0
${LANIP}:/export/secondary /mnt/secondary nfs defaults 0 0
EOF
mount -a

# ===== 4. MySQL =====
apt install -y mysql-server

cat > /etc/mysql/conf.d/cloudstack.cnf <<'EOF'
[mysqld]
server-id=master-01
innodb_rollback_on_timeout=1
innodb_lock_wait_timeout=600
max_connections=350
log-bin=mysql-bin
binlog-format='ROW'
EOF

systemctl restart mysql
systemctl enable mysql

mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_ROOT_PASS}';" || true

# ===== 5. CloudStack APT 저장소 =====
mkdir -p /etc/apt/keyrings
wget -qO- http://download.cloudstack.org/release.asc \
  | gpg --dearmor | tee /etc/apt/keyrings/cloudstack.gpg > /dev/null

echo "deb [signed-by=/etc/apt/keyrings/cloudstack.gpg] http://download.cloudstack.org/ubuntu jammy 4.20" \
  > /etc/apt/sources.list.d/cloudstack.list

apt update

# ===== 6. cloudstack-management =====
apt install -y cloudstack-management

cloudstack-setup-databases cloud:${DB_CLOUD_PASS}@localhost \
  --deploy-as=root:${DB_ROOT_PASS} \
  -e file \
  -m ${MGMT_KEY} \
  -k ${DB_KEY} \
  -i ${LANIP}

cloudstack-setup-management

# ===== 7. cloudstack-agent + libvirt =====
apt install -y qemu-kvm cloudstack-agent
systemctl enable cloudstack-agent

# libvirt TCP listen
sed -i 's|^#vnc_listen.*|vnc_listen = "0.0.0.0"|' /etc/libvirt/qemu.conf
grep -q "^vnc_listen" /etc/libvirt/qemu.conf || echo 'vnc_listen = "0.0.0.0"' >> /etc/libvirt/qemu.conf

cat >> /etc/libvirt/libvirtd.conf <<'EOF'
listen_tls = 0
listen_tcp = 1
tcp_port = "16509"
auth_tcp = "none"
mdns_adv = 0
EOF

cat > /etc/default/libvirtd <<'EOF'
LIBVIRTD_ARGS="--listen"
EOF

systemctl mask libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket libvirtd-tls.socket libvirtd-tcp.socket || true
systemctl restart libvirtd

# AppArmor 비활성
ln -sf /etc/apparmor.d/usr.sbin.libvirtd /etc/apparmor.d/disable/
ln -sf /etc/apparmor.d/usr.lib.libvirt.virt-aa-helper /etc/apparmor.d/disable/
apparmor_parser -R /etc/apparmor.d/usr.sbin.libvirtd 2>/dev/null || true
apparmor_parser -R /etc/apparmor.d/usr.lib.libvirt.virt-aa-helper 2>/dev/null || true

# ===== 8. ARM64 agent.properties (필요시) =====
if [[ "$ARCH" == "aarch64" ]]; then
  cat >> /etc/cloudstack/agent/agent.properties <<EOF

guest.cpu.arch=aarch64
guest.cpu.mode=host-passthrough
network.bridge.type=native
private.bridge.name=cloudbr0
public.network.device=cloudbr0
private.network.device=cloudbr0
guest.network.device=cloudbr0
EOF
fi

systemctl restart cloudstack-agent

# ===== 9. SystemVM Template 등록 =====
/usr/share/cloudstack-common/scripts/storage/secondary/cloud-install-sys-tmplt \
  -m /mnt/secondary \
  -u "${SYSVM_URL}" \
  -h kvm \
  -F

# ===== 완료 =====
cat <<EOF

==============================================================
CloudStack 4.20 단일 노드 설치 완료!
==============================================================

Web UI:   http://${LANIP}:8080/client/
ID:       admin
PW:       password   (첫 로그인 후 반드시 변경)

다음:
  1. Zone 마법사: Advanced Zone, KVM
  2. Pod IP 풀: ${LANIP%.*}.50 ~ ${LANIP%.*}.99
  3. Primary:   NFS ${LANIP}:/export/primary
  4. Secondary: NFS ${LANIP}:/export/secondary
  5. SSVM/CPVM Running 확인 후 첫 VM 배포

로그:
  tail -f /var/log/cloudstack/management/management-server.log
  tail -f /var/log/cloudstack/agent/agent.log

==============================================================
EOF
