# -*- encoding:utf-8 -*-

from kscore.session import get_session

if __name__ == "__main__":
    #获得session
    s = get_session()

    # 如果没有在配置文件.kscore.cfg中设置AK, SK，可通过如下语句设置。
    # s.set_credentials(ak, sk)

    # 创建kec客户端

    client = s.create_client("kec", "cn-beijing-6", use_ssl=False)

    response = client.describe_instances()
    print(response)

    # 获得实例数量
    instance_count = int(response["InstanceCount"])
    print(instance_count)

