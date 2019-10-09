# 金山云Python SDK入门指南
本文描述快速使用金山云Python SDK的过程。

# 1	基础环境
## 1.1	安装python工具
首先需要在调用金山云Python SDK的机器上安装python。当前，金山云Python SDK支持Python 3.7。
```
michaeldembp-2:venv myang$ python3 --version
Python 3.7.3
```

## 1.2	创建Python环境
为了避免Python开发环境的相互影响，建议创建一个独立的Python环境。
```
michaeldembp-2:venv myang$ pwd
/Users/myang/venv
michaeldembp-2:venv myang$ python3 -m venv ksyun
michaeldembp-2:venv myang$ source ksyun/
bin/        include/    lib/        pyvenv.cfg  
michaeldembp-2:venv myang$ source ksyun/bin/activate
(ksyun) michaeldembp-2:venv myang$ python --version
Python 3.7.3

ksyun) michaeldembp-2:venv myang$ which pip
/Users/myang/venv/ksyun/bin/pip
(ksyun) michaeldembp-2:venv myang$ pip list
Package    Version
---------- -------
pip        19.0.3 
setuptools 40.8.0 
You are using pip version 19.0.3, however version 19.2.3 is available.
You should consider upgrading via the 'pip install --upgrade pip' command.
(ksyun) michaeldembp-2:venv myang$ pip install --upgrade pip
Collecting pip
  Downloading https://files.pythonhosted.org/packages/30/db/9e38760b32e3e7f40cce46dd5fb107b8c73840df38f0046d8e6514e675a1/pip-19.2.3-py2.py3-none-any.whl (1.4MB)
    100% |████████████████████████████████| 1.4MB 865kB/s 
Installing collected packages: pip
  Found existing installation: pip 19.0.3
    Uninstalling pip-19.0.3:
      Successfully uninstalled pip-19.0.3
Successfully installed pip-19.2.3
(ksyun) michaeldembp-2:venv myang$ pip list
Package    Version
---------- -------
pip        19.2.3 
setuptools 40.8.0
```
# 2	安装金山云Python SDK
首先从Github上获得最新的金山云Python SDK。
```
(ksyun) michaeldembp-2:temp myang$ pwd
/Users/myang/temp
(ksyun) michaeldembp-2:temp myang$ git clone https://github.com/KscSDK/ksc-sdk-python.git
Cloning into 'ksc-sdk-python'...
remote: Enumerating objects: 155, done.
remote: Counting objects: 100% (155/155), done.
remote: Compressing objects: 100% (112/112), done.
remote: Total 1971 (delta 81), reused 62 (delta 21), pack-reused 1816
Receiving objects: 100% (1971/1971), 1.33 MiB | 238.00 KiB/s, done.
Resolving deltas: 100% (1024/1024), done.
```

然后执行python setup.py install，完成金山云Python SDK的安装。
```
(ksyun) michaeldembp-2:ksc-sdk-python myang$ pwd
/Users/myang/temp/ksc-sdk-python
(ksyun) michaeldembp-2:ksc-sdk-python myang$  python setup.py install

(ksyun) michaeldembp-2:ksc-sdk-python myang$  pip list
Package         Version
--------------- -------
docutils        0.15.2 
jmespath        0.9.4  
ksc-sdk-python  1.3.21 
pip             19.2.3 
python-dateutil 2.8.0  
PyYAML          3.13   
setuptools      40.8.0 
six             1.12.0
```
# 3	编写金山云Python SDK范例
3.1	配置AK/SK
在范例程序所处的目录下，创建.kscore.cfg，该文件包含金山云账户的AK/SK。为了安全起见，建议使用具有特定访问权限的子用户的AK/SK。下面是.kscore.cfg的内容.
```
[Credentials]
ks_access_key_id=[your ak]
ks_secret_access_key=[your sk]
```
## 3.2	编写范例
该范例是调用describe_instances方法，返回特定InstanceId的云服务器实例信息。
``` python
from kscore.session import get_session

if __name__ == "__main__":
    #获得session
    s = get_session()

    # 如果没有在配置文件.kscore.cfg中设置AK, SK，可通过如下语句设置。
    # s.set_credentials(ak, sk)

    # 创建kec客户端
    client = s.create_client("kec", "cn-beijing-6", use_ssl=False)

    #设置describe_instances方法参数
    param = {
        "InstanceId.1": "24fd30b9-d222-490d-9212-acb138c12074"
    }

    response = client.describe_instances(**param)
    print(response)

    # 获得实例数量
    instance_count = int(response["InstanceCount"])
    print(instance_count)
```
然后执行如下命令，确认调用金山云OpenAPI成功。
```
MichaeldeMacBook-Pro-2:keepalived-ha myang$ python kec.py
{u'Marker': 0, u'InstanceCount': 8, u'InstancesSet': [{u'Monitoring': {u'State': u'enabled'}, u'InstanceState': {u'Name': u'active'}, u'ProductType': 152, u'AutoScalingType': u'Auto', u'ProductWhat': 1, u'IsShowSriovNetSupport': False, u'PrivateIpAddress': u'10.0.22.18', u'InstanceId': u'24fd30b9-d222-490d-9212-acb138c12074', u'SriovNetSupport': u'false',
```