# 通过Keepalived实现金山云自建服务高可用

用户在金山云上部署应用时，如需要MySQL, Redis等服务，建议尽量采用金山云提供的PaaS服务（比如关系型数据库-MySQL，云数据库Redis等)。金山云负责这些PaaS服务的高可用，并提供便捷管理和可视化监控告警功能。但当某些服务金山云不具有，或者用户需要对服务具有更灵活的管理能力，用户可以在金山云云服务器上自己安装和配置服务，利用主备两台服务器实现服务高可用，并通过Keepalived实现单服务器故障后虚拟IP自动漂移，缩短RTO(Recovery Time Object，恢复时间目标)，从而提高整个应用的高可用水平。

本方案的架构参考如下：

![金山云自建服务高可用架构示意图](https://raw.githubusercontent.com/ksc-sbt/keepalived-ha/master/keepalived-ha-arch.png)

本指南包含如下内容：
* 准备实验环境；
* 配置Keepalived实现虚拟IP漂移；
* 启用Keepalived服务；
* 测试故障切换。

# 1 准备实验环境
本指南所使用的环境位于金山云北京6区。

## 1.1 VPC配置信息

|  网络资源   | 名称  | CIDR  |
|  ----  | ----  | ----  |
| VPC  | sbt-vpc |	10.34.0.0/16 |

## 1.2 子网配置信息

| 子网名称 | 所属VPC |可用区 | 子网类型  | CIDR  | 说明|
|  ----  | ----  | ----  |----  |----  |----|
| public_a  | sbt-vpc |	可用区A | 普通子网| 10.34.51.0/24|用于跳板机|
| private_a  | sbt-vpc |	可用区A | 普通子网| 10.34.0.0/20|用于云服务器|


## 1.3 安全组配置信息
作为实验环境，创建安全组ha-sg，该安全组允许云服务器可以被任意主机访问：

|协议|行为|起始端口|结束端口|源IP|
|----|----|----|----|----|
|IP|允许|-|-|0.0.0.0/0|


## 1.4 NAT配置信息
由于云服务器需要能访问金山云OpenAPI，因此需要配置公网NAT实例。下面是NAT实例的配置信息。

|名称|所属VPC|作用范围|类型|所绑定的子网|
|  ----  | ----  | ----  |----  |----  |
|Ksc_Nat|sbt-vpc|绑定的子网|公网|private_a|

## 1.5 云服务器信息
|名称|类型|所属于VPC|所属子网|配置|IPV4地址|安全组|操作系统|登录方式
|  ----  | ----  | ----  |----  |----  |----  |----  |----  |----  |
|ymq-srv-1|通用型N3|sbt-vpc|private_a|8核32G|10.32.0.2|ha-sg|CentOS Linux release 7.7.1908 (Core)|密码|
|ymq-srv-2|通用型N3|sbt-vpc|private_a|8核32G|10.32.0.3|ha-sg|CentOS Linux release 7.7.1908 (Core)|密码|

## 1.6 安装配置Nginx
为了便于测试虚拟IP漂移效果，在主、备云主机上安装Nginx，并修改 /usr/share/nginx/html/index.html内容来区分主、备云主机。
```
[root@sbt-basition ~]# curl 10.34.0.2
Master
[root@sbt-basition ~]# curl 10.34.0.3
Slave
```
## 1.7 准备金山云OpenAPI环境
两台云服务器都需要能访问金山云OpenAPI，配置过程请参见[《金山云Python SDK入门指南》](
https://github.com/ksc-sbt/keepalived-ha/blob/master/%E9%87%91%E5%B1%B1%E4%BA%91Python%20SDK%E5%85%A5%E9%97%A8%E6%8C%87%E5%8D%97.md)

# 2 配置Keepalived实现虚拟IP漂移
## 2.1 Keepalived环境准备
在两台服务器上都安装Keepalived，然后确认keepalived版本是v1.3.5。
```
[root@srv001 ~]# yum install keepalived -y
[root@srv001 ~]# keepalived --version
Keepalived v1.3.5 (03/19,2017), git commit v1.3.5-6-g6fa32f2
 ```
在/etc/keepalived/目录下，从github上获得三个配置文件：
```
wget  https://raw.githubusercontent.com/ksc-sbt/keepalived-ha/master/keepalived.conf
wget  https://raw.githubusercontent.com/ksc-sbt/keepalived-ha/master/notify_action.sh
wget  https://raw.githubusercontent.com/ksc-sbt/keepalived-ha/master/nexthop.py
```
## 2.2 修改keepalived.conf
下面是下载的原始keepalived.conf文件。
```! Configuration File for keepalived
vrrp_instance VI_1 {
  state BACKUP
  interface eth0 #改成本机网卡名 例如 eth0
  virtual_router_id 51
  priority 90 # 无常主模式，Keepalived两个节点优先级相同，避免自动切换
  advert_int 1

  authentication {
    auth_type PASS
    auth_pass Passw0rd
  }

  unicast_src_ip 10.34.0.2 # 修改本机内网 IP
  unicast_peer {
    10.34.0.3 #修改为对端设备的 IP 地址
  }

  virtual_ipaddress {
    10.34.0.200/20 dev eth0  #修改为内网 VIP
  }

  notify_master "/etc/keepalived/notify_action.sh MASTER"
  notify_backup "/etc/keepalived/notify_action.sh BACKUP"
  notify_fault "/etc/keepalived/notify_action.sh FAULT"
  notify_stop "/etc/keepalived/notify_action.sh STOP"
}
```
在主云服务器(10.34.0.2)上，修改如下内容，其中Passw0rd是两台服务器的root口令。10.34.0.2是本地IP地址，而10.34.0.3是从服务器IP地址。10.34.0.200/20 dev eth0表示在eth0网卡上绑定虚拟IP 10.34.0.200/20。
```
  authentication {
    auth_type PASS
    auth_pass Passw0rd
  }

  unicast_src_ip 10.34.0.2 # 修改本机内网 IP
  unicast_peer {
    10.34.0.3 #修改为对端设备的 IP 地址
  }
   virtual_ipaddress {
    10.34.0.200/20 dev eth0  #修改为内网 VIP
  }
  ```
  在从云服务器上(10.34.0.3上)，交换unicast_src_ip和unicast_peer参数。
  ```
  unicast_src_ip 10.34.0.3 # 修改本机内网 IP
  unicast_peer {
    10.34.0.2 #修改为对端设备的 IP 地址
  }
```
## 2.3 检查notify_action.sh文件
当Keepalived服务检测到异常，并切换主、备状态时，将调用该脚本。
在本脚本中，“source /root/kec-ha/bin/activate”是为了激活安装了金山云Python SDK的python环境。其中/root/kec-ha是python环境目录。

```
#!/bin/bash
#/etc/keepalived/notify_action.sh

source /root/kec-ha/bin/activate

log_file=/var/log/keepalived.log
log_write()
{
    echo "[`date '+%Y-%m-%d %T'`] $1" >> $log_file
}

[ ! -d /var/keepalived/ ] && mkdir -p /var/keepalived/

case "$1" in
    "MASTER" )
        echo -n "$1" > /var/keepalived/state
        log_write " notify_master"
        echo -n "0" > /var/keepalived/vip_check_failed_count
        python /etc/keepalived/nexthop.py migrate >> $log_file  2>&1 &
        ;;

    "BACKUP" )
        echo -n "$1" > /var/keepalived/state
        log_write " notify_backup"
        ;;

    "FAULT" )
        echo -n "$1" > /var/keepalived/state
        log_write " notify_fault"
        ;;

    "STOP" )
        echo -n "$1" > /var/keepalived/state
        log_write " notify_stop"
        ;;
    *)
        log_write "notify_action.sh: STATE ERROR!!!"
        ;;
esac
```
## 2.4 修改nexthop.py文件
最初的nexthop.py脚本如下。该脚本通过调用金山云OpenAPI，创建一条主机路由，该路由的目标网段为10.34.0.200/32，下一跳为当前启用的云服务器实例ID。

```python
#!/root/kec-ha/bin/python
# -*- coding: utf-8 -*-
#/etc/keepalived/nexthop.py

import os
import time
import json
import sys
from kscore.session import get_session

##################需修改部分Begin####################
region='cn-beijing-6'   #region code
vpcId = 'c7f060c0-6d0d-4adb-987f-fda1fc988ffe'  #vpcId
ks_access_key_id = 'Your AK'
ks_secret_access_key = 'Your SK'
DestinationCidrBlock = '10.34.0.200/32' #修改为VIP 
thisInstanceId = '8db8ae25-1281-47a0-8155-47c6ed37e876' #当前主机的Id
##################需修改部分End######################

log = open('/var/log/keepalived.log', 'a+')
#state_file = open('/var/keepalived/state', 'r')

def get_now_time():
    return time.strftime('[%Y-%m-%d %H:%M:%S]',time.localtime(time.time())) + '[pid' + str(os.getpid()) + ']' 

def log_write(message=''):
    log.write(get_now_time() + " " + str(message) + "\n")


def findRoute():
    for route in vpcClient.describe_routes()['RouteSet']:
        if route['DestinationCidrBlock'] == DestinationCidrBlock:
            log_write('an existing route found')
            return route['RouteId']
    log_write('route not found')

def migrateVip():
    param={'VpcId':vpcId,
            'DestinationCidrBlock':DestinationCidrBlock,
            'RouteType':'Host',
            'InstanceId':thisInstanceId}
    log_write("migrating vip to another host.")
    time.sleep(0.5)
    r = findRoute()
    if r:
        vpcClient.delete_route(RouteId=r)
    log_write(" now change the nexthop of vip to this host." + thisInstanceId)
    if vpcClient.create_route(**param):
                log_write('migrating vip success')

def print_help():
    log_write(
            '''
            ./nexthop.py migrate
                migrate your vip
            ''')

if __name__ == '__main__':
    s = get_session()
    s.set_credentials(ks_access_key_id,ks_secret_access_key)
    vpcClient = s.create_client("vpc", region, use_ssl=True)
    if len(sys.argv) == 1:
        log_write("nexthop.py: parameter num is 0")
        print_help()
    elif sys.argv[1] == 'migrate':
        migrateVip()   
        log_write()
    else:
        log_write("nexthop.py: misMatched parameter")
        print_help()
```
首先的在两台云服务器上替换nexthop.py中region， vpcID, AK/SK, DestinationCidrBlock等信息。
```python
##################需修改部分Begin####################
region='cn-beijing-6'   #region code
vpcId = 'c7f060c0-6d0d-4adb-987f-fda1fc988ffe'  #vpcId
ks_access_key_id = 'Your AK'
ks_secret_access_key = 'Your SK'
DestinationCidrBlock = '10.34.0.200/32' #修改为VIP 
thisInstanceId = '8db8ae25-1281-47a0-8155-47c6ed37e876' #当前主机的Id
##################需修改部分End######################
```
其中thisInstanceId是本机的云服务器实例ID。通过金山云控制台，能获得云服务器的ID信息分别如下：
|云服务器名称|实例ID|
|----|----|
|ymq-srv-1|62ae8ff8-5c84-4c08-b8e3-2912d9fa5c4e|
|ymq-srv-2|8db8ae25-1281-47a0-8155-47c6ed37e876|
因此在主云服务器上，修改nexthop.py为如下：
```python
thisInstanceId = '62ae8ff8-5c84-4c08-b8e3-2912d9fa5c4e' #当前主机的Id
```
因此在从云服务器上，修改nexthop.py为如下：
```python
thisInstanceId = '8db8ae25-1281-47a0-8155-47c6ed37e876' #当前主机的Id
```
# 3 启用Keepalived

## 3.1 检查初始状态
首先保证两台云服务器的keepalived服务处于停止状态。
```bash
[root@srv001 ~]# service keepalived status
Redirecting to /bin/systemctl status keepalived.service
...
Oct 09 13:48:34 srv001 systemd[1]: Stopped LVS and VRRP High Availability Monitor.
```
确认云服务器的主网卡eth0只绑定了一个IP。
```
[root@srv001 ~]# ip addr 
...
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether fa:16:3e:73:06:1a brd ff:ff:ff:ff:ff:ff
    inet 10.34.0.2/20 brd 10.34.15.255 scope global eth0
       valid_lft forever preferred_lft forever

此时，在另外一个服务器上，确认两台服务器的Nginx服务运行正常，但不能通过VIP访问。
```bash
[root@sbt-basition ~]# curl 10.34.0.2
Master
[root@sbt-basition ~]# curl 10.34.0.3
Slave
[root@sbt-basition ~]# curl 10.34.0.200

^C
[root@sbt-basition ~]# 
```
## 3.2 启用主云服务器上的keepalived服务
启动keepalived服务。
```bash
[root@srv001 ~]#  service keepalived start
Redirecting to /bin/systemctl start keepalived.service
```
运行ip addr命令，确认10.34.0.200已经绑定到eth0网卡上。
```bash
[root@srv001 ~]# ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether fa:16:3e:73:06:1a brd ff:ff:ff:ff:ff:ff
    inet 10.34.0.2/20 brd 10.34.15.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet 10.34.0.200/20 scope global secondary eth0
       valid_lft forever preferred_lft forever
```
检查/var/log/keepalived.log文件，能看到如下日志信息。
```
[2019-10-09 13:55:48]  notify_master
[2019-10-09 13:55:48][pid55063] migrating vip to another host.
[2019-10-09 13:55:49][pid55063] an existing route found
[2019-10-09 13:55:49][pid55063]  now change the nexthop of vip to this host.62ae8ff8-5c84-4c08-b8e3-2912d9fa5c4e
[2019-10-09 13:55:50][pid55063] migrating vip success
[2019-10-09 13:55:50][pid55063] 
```
访问金山云控制台，能看到如下路由信息。
![VPC中更新的路由表信息](https://raw.githubusercontent.com/ksc-sbt/keepalived-ha/master/route-srv1.png)
此时，再次访问VIP，确认VIP已经能被访问。
```bash
[root@sbt-basition ~]# curl 10.34.0.200
Master
You have new mail in /var/spool/mail/root
[root@sbt-basition ~]# traceroute 10.34.0.200
traceroute to 10.34.0.200 (10.34.0.200), 30 hops max, 60 byte packets
 1  10.34.0.200 (10.34.0.200)  0.308 ms  0.275 ms  0.266 ms
[root@sbt-basition ~]# 
```
## 3.3 启用从云服务器上的keepalived服务
在从服务器上，启动keepalived服务。
```
[root@srv002 keepalived]# service keepalived start
```

检查/var/log/keepalived.log文件，能看到如下日志信息。
```
[2019-10-09 14:03:37]  notify_backup
```
因此从服务器当前的状态是BACKUP，因此在网卡上不会被绑定VIP。
```bash
[root@srv002 keepalived]# ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether fa:16:3e:3e:a9:57 brd ff:ff:ff:ff:ff:ff
    inet 10.34.0.3/20 brd 10.34.15.255 scope global eth0
       valid_lft forever preferred_lft forever
[root@srv002 keepalived]# 
```
# 4 测试故障切换
首先在另外一台服务器上运行如下脚本，持续访问VIP。
```
[root@sbt-basition ~]# while true; do curl http://10.34.0.200; sleep 2; done
Master
Master
```
## 4.1 测试场景1: 停掉主服务器的Keepalived服务
```
[root@srv001 ~]# service keepalived stop
```
此时在测试机上，能看到如下信息。表明现在已经切换为从服务器提供服务。
```
Master
Slave
Slave
```
再次启动主服务器上服务，keepalived不会自动切回主服务器，因为在keepalived.conf中设置为“state BACKUP  #无常主模式初始角色”。
```
[root@srv001 ~]# service keepalived start
```

## 4.2 测试场景2: 停掉从服务器的Keepalived服务
停止从服务器的Keepalived服务，Nginx服务将被切回主服务器。
```
[root@srv002 keepalived]# service keepalived stop
```
测试机输出信息:
```
Slave
Master
Master
```
## 4.3 测试场景3：停止主服务器

首先确保当前是主服务器在提供服务，同时从服务器的keepalived服务处于启动状态。
主服务器绑定了VIP。
```bash
[root@srv001 ~]# ip addr
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether fa:16:3e:73:06:1a brd ff:ff:ff:ff:ff:ff
    inet 10.34.0.2/20 brd 10.34.15.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet 10.34.0.200/20 scope global secondary eth0
       valid_lft forever preferred_lft forever
```
从服务器的Keepalived服务处于启动状态。
```bash
[root@srv002 ~]# service keepalived status
Redirecting to /bin/systemctl status keepalived.service
● keepalived.service - LVS and VRRP High Availability Monitor
   Loaded: loaded (/usr/lib/systemd/system/keepalived.service; enabled; vendor preset: disabled)
   Active: active (running) since Wed 2019-10-09 16:18:31 CST; 3s ago
  Process: 70257 ExecStart=/usr/sbin/keepalived $KEEPALIVED_OPTIONS (code=exited, status=0/SUCCESS)
 Main PID: 70258 (keepalived)
   CGroup: /system.slice/keepalived.service
           ├─70258 /usr/sbin/keepalived -D
           ├─70259 /usr/sbin/keepalived -D
           └─70260 /usr/sbin/keepalived -D

Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: Registering Kernel netlink co...l
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: Registering gratuitous ARP sh...l
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: Opening file '/etc/keepalived....
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: WARNING - default user 'keepa....
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: SECURITY VIOLATION - scripts ....
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: VRRP_Instance(VI_1) removing ....
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: Using LinkWatch kernel netlin....
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: VRRP_Instance(VI_1) Entering ...E
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: Opening script file /etc/keep...h
Oct 09 16:18:31 srv002 Keepalived_vrrp[70260]: VRRP sockpool: [ifindex(2), p...]
Hint: Some lines were ellipsized, use -l to show in full.
[root@srv002 ~]# 
```
通过金山云控制台强制停止主服务器，或者在主服务器上执行shutdown命令。同时在从服务器上执行tail命令：
```
[root@srv002 ~]# tail -f /var/log/keepalived.log 
...
[2019-10-09 16:20:47]  notify_master
[2019-10-09 16:20:47][pid70394] migrating vip to another host.
[2019-10-09 16:20:48][pid70394] an existing route found
[2019-10-09 16:20:48][pid70394]  now change the nexthop of vip to this host.8db8ae25-1281-47a0-8155-47c6ed37e876
[2019-10-09 16:20:49][pid70394] migrating vip success
[2019-10-09 16:20:49][pid70394] 
```
通过上述日志，表明在主服务器宕机时，将自动化切换到从服务器。
# 5 总结
本文介绍了通过Keepalived，实现虚拟IP在不同云主机之间的自动漂移，并通过在主、从切换时自动运行脚本调用金山云配置主机路由，实现两台云服务器能被外部用一个IP地址访问。此外，由于金山云主机路由的下一跳不仅仅可以是云服务器，还可以是云物理主机，因此，采用该方法也可以实现在金山云云物理主机上自建高可用服务。
