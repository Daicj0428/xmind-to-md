本文档最新更新地址，如果当前文档未找到解决方法，可尝试到最新地址上查找看看：   
云桌面内网（持续更新）：http://git.one/linnankun/snc-ng-proxy-agent-demo/blob/master/FAQ.md
公司内网（不定期更新）：http://192.168.50.167:8090/pages/viewpage.action?pageId=44174015

# 程序自带的测试工具

从0.2.0版本开始新增了命令测试的工具用于排查问题，proxy和agent用法一样。   
可通过下面命令查看当前版本支持的测试命令

```shell
java -jar snc-ng-proxy*.jar cmd help
```

使用测试命令，cmd是必填

```shell
# 查询安装包信息
java -jar snc-ng-proxy*.jar cmd version
# 查看当前程序配置文件的配置项说明
java -jar snc-ng-proxy*.jar cmd configDesc
# 查看当前程序支持的监控项
java -jar snc-ng-proxy*.jar cmd metricKeyDesc
# 测试监控项采集，注意windows系统不能使用单引号括注参数，`process.cpu`为对应的监控项key值
java -jar snc-ng-proxy*.jar cmd 'metric=process.cpu' host=proxyIp:monitorPort
# 测试本地命令，如果参数值有空格，参数名和参数值要用单引号括起来
java -jar snc-ng-proxy*.jar cmd 'commandTest=echo hello'
```

# 常见问题解决

**重点说明**
1. 如果遇到问题需要技术人员协助的，请先按第3点尝试找相关的日志后再联系技术人员协助。
2. snc-ng-proxy与snc-ng-agent绝大部分功能是一样的，所以proxy和agent的问题排查方式也基本是一样的。
3. 如果遇到问题，请先查看对应服务的日志：
   1. 用proxy跑的功能就看proxy的日志。
   2. 用agent跑的功能先看agent日志，agent没问题就再看proxy的日志。
   3. 如果agent和proxy都没找到可疑的日志，就到功能失败对应的微服务下找可疑的日志。
4. 如果问题的错误提示包含了`FAQ:xxx`关键字，`xxx`为问题编号，可以在本文档搜索编号找对应的解决方法。
5. snc-ng-proxy和snc-ng-agent的功能基本一样，所以相同的功能，配置也是通用的，proxy配置固定以`proxy.`开头，agent配置固定以`agent.`开头。


## 一、插件已安装，但前端没看到有注册上来（错误码：13005）

1. 确定plugin.json插件描述文件的pluginEnglishName的值写代码里的一致。
2. 确定plugin.json插件描述文件的schedulable的值与插件的类型一致，true为执行插件ExecutablePlugin的子类，false为常驻型插件BackgroundPlugin的子类。
3. 开启DEBUG或TRACE级别日志，看是否有扫描到插件，正常会有插件英文名输出，搜索相关日志，并查看是否有相关提示，如果没有相关日志，就是插件没扫描到，确认插件类的包路径是在com.shsnc.**下。
4. 查看snc-manager-up的topic里的上报信息，找到上报记录，确认是否有上报对应插件信息，上报信息内会包含pluginInfo字段。
5. 如果有上报插件信息，查看snc-ng-server日志，看是否有错误日志。

## 二、任务不下发不运行不停止和任务长时间未上报等问题（错误码：20006）

首先确认执行目标proxy或agent是否在线，或尝试重启proxy或agent解决，然后再根据下面流程排查：

### 快速排查

- 从任务管理列表或查数据库等方式，看任务的错误信息字段是否有描述失败原来。
- 从任务管理列表或查数据库等方式，看任务的执行状态是什么状态，根据状态分析任务失败的环节再进行下一步的排查
- 如果确认任务已下发下去，到对应的proxy或agent服务上，开启DEBUG级别日志，甚至可以开启TRACE级别，根据关键字“`- {taskId}`”可过滤该任务相关日志做分析，`{taskId}`为下发时的任务id，注意中间有空格。


### 下面是任务在前端保存成功后的执行流程，根据流程逐步排查，一般对应服务会打印对应的日志：

- 指定proxy或agent执行的流程：
    1. 执行目标通过kafka的snc-manager-up发送消息定时主动拉取任务，kafka消息内容的tasksGet字段为任务更新时间，每次只拉取这个时间之后更新的任务。
    2. snc-ng-server消费snc-manager-up消息，根据tasksGet字段查询目标在这个时间之后更新的任务，然后通过目标所属的集群组topic下发任务，默认topic是snc-message-default。
    3. 执行目标通过消费集群组topic消息来接收任务消息，然后执行任务。
- 指定集群组执行的流程：
    1. snc-ng-server定时30秒扫描出当前90秒以上（连接3次心跳的时间）未上报任务状态的任务和新任务。
    2. snc-ng-server根据任务所属集群组判断是否还有proxy在线，然后再发送任务消息到该集群组topic，随机其中一个proxy消费执行。
    3. 如果任务正常执行，在任务信息表snc_task的target_id字段会记录当前执行任务的proxy的id。
- 任务停止流程跟指定proxy或agent执行流程一样，在拉取任务时候如果任务是禁用状态，会下发一个停止任务的任务给执行目标。对于执行目标为集群组的，则根据target_id字段给当前执行目标下发停止任务。

### 任务未下发成功（错误码：13009）
1. 先确认任务所属的代理是否离线，需要在线才能下发任务。
2. 查看snc-ng-server日志是否出现“已在检查XXX[xxx]的任务更新情况”
    - 检查redis缓存是否存在key:`SNC_NG_SVR:send_task:xxx`并且未设置过期时间，如果存在删除该key即可。
3. 如果是某个代理下其中一个或几个任务未下发成功
    - 检查redis缓存是否存在key:`SNC_NG_SVR:task:starting:{taskId}`并且未设置过期时间，如果存在删除该key即可，其中{taskId}为任务id。
4. 如果redis缓存未找到对应的key，尝试编辑再保存一下任务，或重启代理，再触发一次任务下发。


## 三、proxy日志频繁出现`kafka启动，assigned partitions: 1,2,3`

出现该日志主要原因是proxy接收消费的topic不停的在重平衡，可能是proxy集群下proxy数多并且连接kafka不稳定。   
尝试将集群下所有proxy增加以下配置解决：

```properties
# 默认值6000
proxy.kafka.consumer.session.timeout.ms=60000
# 默认值2000
proxy.kafka.consumer.heartbeat.interval.ms=15000
```

## 四、日志频繁出现 `channel[ip:port] can not write`

出现该日志主要原因netty发送数据通道缓存已满，多数是传文件的时候出现。偶尔出现不影响。    
如果频繁出现或已影响到功能运行了，出现问题的服务可加下面配置解决（不需要proxy和agent同时加）：

```properties
### proxy 配置
# proxy 默认25M
proxy.netty.writeBufferWaterMarkLow=26214400
# proxy 默认50M
proxy.netty.writeBufferWaterMarkHigh=52428800
### agent 配置
# agent 默认5M
agent.netty.writeBufferWaterMarkLow=5242880
# agent 默认10M
agent.netty.writeBufferWaterMarkHigh=10485760
```

## 五、agent日志频繁出现 `netty ip:port unwritable`

出现该日志主要原因agent通过netty向proxy发送数据通道缓存已满，偶尔出现不影响。    
如果频繁出现或已影响到功能运行了，可增加proxy分担压力，或在agent加下面配置尝试解决：

```properties
### agent 配置
# agent 默认5M
agent.netty.writeBufferWaterMarkLow=5242880
# agent 默认10M
agent.netty.writeBufferWaterMarkHigh=10485760
```

## 六、SSH连接被中断【ssh版本不一致】;SSH连接信息为：xxx.xxx.xxx.xxx,sshUser为：xxx

- 问题现象 通过ssh方式执行命令或脚本时返回上面的提示。 日志文件中出现异常信息：`com.jcraft.jsch.JSchException: Algorithm negotiation fail`。
- 问题原因 目标服务器的ssh与proxy或agent的加密算法不一致，无法进行加密通信。一般是目标服务器的ssh版本过低，算法过旧。
- 解决方法
    - 方法一：升级目标服务器的ssh版本。
    - 方法二：修改proxy或agent配置文件，增加对应过时的算法
        ```
        # proxy配置
        proxy.ssh.kex=diffie-hellman-group1-sha1
        proxy.ssh.serverHostKey=ssh-rsa,ssh-dss0
        # agent配置
        agent.ssh.kex=diffie-hellman-group1-sha1
        agent.ssh.serverHostKey=ssh-rsa,ssh-dss0
        ``` 
      通过下面两个方式之一查目标服务器ssh支持的算法：
        - 方式一：在客户端执行查看命令：`ssh -vvv 目标服务器ip`，找到下面内容：
          ```
          debug2: KEX algorithms: diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1,diffie-hellman-group1-sha1
          debug2: host key algorithms: ssh-rsa,ssh-dss
          ```
          关键字 `KEX algorithms` 后面对应的是 `ssh.kex` 配置。   
          关键字 `host key algorithms` 后面对应的是 `ssh.serverHostKey` 配置。
        - 方式二：在服务器上执行查看命令：`ssh -Q kex; ssh -Q key; ssh -Q cipher; ssh -Q mac`

## 七、启动报“获取本机MAC地址出现异常”

- 问题现象   
   日志文件中只出现`获取本机MAC地址出现异常`这个异常错误信息，并且没有其他日志信息。
- 问题原因 
   服务器上配了多个dns解析。
- 解决方法 
  - 只保留一个dns解析。
  - 例如：注释掉 /etc/resolv.conf 里面的内容
- 启动脚本增加jvm参数指定使用其中一个dns：-Dsun.net.spi.nameservice.nameservers=8.8.8.8 （未验证）

## 八、脚本执行不了相关问题

先找一下下面以前遇到过的一些proxy或agent无法执行脚本的情况，看有没有相似的场景和解决方法，如果没用，就按下面方法排查一下

#### 自排查方法

使用程序自带的测试工具`commandTest`测试进行下面一些测试

- 执行一下脚本，分析返回执行结果和查看日志文件有没有输出什么错误或异常   
  `java -jar snc-ng-agent*.jar cmd "commandTest=sh /{script_file.sh}"`
  0.4.1版本可增加`debug`参数设置日志级别：`java -jar snc-ng-agent*.jar cmd debug "commandTest=sh /{script_file.sh}"`
- 输出程序执行的环境变量，与用户直接执行的环境变量做对比   
  linux: `java -jar snc-ng-agent*.jar cmd "commandTest=env"`
  window: `java -jar snc-ng-agent*.jar cmd commandTest=set`

#### 脚本执行结果与手动执行不一样
1. 执行代理开启debug级别日志（即最终执行的proxy或agent）
2. 触发执行脚本的功能并关注日志输出，找出代理执行脚本的命令，并对比手动执行脚本的命令的差别，两边的执行脚本命令需要一致。
    - 如果是执行临时脚本，可以给proxy或agent添加以下配置保留临时脚本用于排查问题：`<proxy|agent>.exec.temp.file.clean=false`
3. 如果日志输出的命令与手动执行不一样，就复制日志的命令出来执行，如果结果还是不一样，就需要调整上层服务功能下发的命令，请联系对应功能的产品负责人排查处理。
4. 如果日志里面的命令与预期的一样，则可能是环境变量不一样，执行下面命令查询代理的环境变量并对比直接查询环境变量的差异，并在脚本中添加或修改环境变量。
   linux: `java -jar snc-ng-agent*.jar cmd "commandTest=env"`
   window: `java -jar snc-ng-agent*.jar cmd commandTest=set`

#### 湖南电信部分agent执行脚本报无权限错误 

- 环境
    - 系统：Red Hat 4.8.5-11
    - 旧版agent版本：1.3.8
- 问题现象 使用agent本地方式执行脚本，无论执行任何脚本，都会执行失败，报错误信息：`bash: /usr/bin/sh: Permission denied`
- 排查过程
    - 查看 `/usr/bin/bash` `/usr/bin/sh` 和上面每一级目录都已经给了执行权限，和脚本也给了执行权限，还是报错。
    - 使用agent启动用户按照代码执行脚本命令方式 `bash -c "/tmp/snc_agent_tmp/xxx.sh"` 却能正常执行。
    - 与正常执行的agent对比了系统版本，bash版本，系统环境变量，并无差异。
    - 尝试不使用`bash -c`直接执行脚本，命令：`/tmp/snc_agent_tmp/xxx.sh`，脚本需要给执行权限，并第一行指定`#!/bin/sh`
      。然后执行会报错误信息：`bad interpreter: Permission denied`.
    - 根据错误找到问题说明，具体原因说不清，大概是分区挂载的问题。
      - https://www.cnblogs.com/linyfeng/p/11087655.html
      - http://xcd.blog.techweb.com.cn/archives/122.html
- 解决方法
    - 添加配置`agent.dir.temp={agent_home}/snc_agent_tmp`，将生成脚本的临时目录放到agent的安装目录下。

#### aix系统通过脚本采集oracle数据库性能无数据返回

- 问题现象   
  agent执行脚本无结果返回，，开启debug级别日志，日志输出了脚本执行的错误信息：`0509-360 Cannot load program /osw/ogg/ggsci because of the following error:`

- 问题原因    
  脚本需要设置环境变量指定 ODBC 的动态链接库，aix系统与其它linux系统设置的变量名不一样，一般linux系统是设置`LD_LIBRARY_PATH`这个环境变量，aix系统需要设置`LIBPATH`这个环境变量。   
  参考链接：https://www.ibm.com/docs/zh/informix-servers/12.10?topic=products-libpath-environment-variable-unix

- 解决方法   
  执行脚本同时设置`LD_LIBRARY_PATH`和`LIBPATH`这两个环境变量。

#### 执行脚本出现异常：Executable can not be null

- 问题现象   
  agent执行任务脚本或命令结果都会出现异常`Executable can not be null`，查看agent启动时的日志也现出了日志内容`can't find shell`。

- 问题原因   
  agent识别系统命令环境失败，无法识别到`bash`、`sh`和`ksh`的命令执行环境。可能是jre文件的执行权限问题。

- 解决方法   
  给jre目录赋予执行权限：chmod -R +x ./jre

#### Windows执行脚本出现异常： Cannot run program "cmd.exe" (in directory"."): CreateProcess error=5，拒绝访问。
南航现场发现该问题是因为系统杀毒软件禁止执行cmd程序了，如果遇到该问题，请确认主机是否有安装并启动类似功能的软件。


## 九、agent无法连接proxy

#### 日志出现下面错误信息及解决方法
- Caused by: java.net.SocketException: No buffer space available (maximum connections reached?): bind
  - 原因：proxy或agent可能无法创建连接端口
  - 解决1：先确认proxy和agent是否创建端口，使用telnet命令测试连接任意可连接的端口。如果没有telnet，使用《程序自带的测试工具》的端口测试命令测试
  - 解决2：确认用户是否正常，使用其它正常连接外部端口的用户启动服务。如：linux的root用户，windows的Administrator用户。


## 十、agent上报上来后无集群信息
- 问题原因      
  proxy上报的ip与agent配置的proxy ip不一致。

- 解决方法
    - 原因一：proxy机器是多网卡，在配置文件中指定proxy的ip为agent配置的ip，proxy上报的ip和要agent配置的proxyIp一致。
    - 原因二：网络策略原因，agent连接的不是proxy的真正ip，解决方法：
      - proxy增加配置：`proxy.ignore.check.ip=true`。
      - proxy的ip配置设为agent连接的ip。
      - 这种解决方式可能会导致proxy无法启停重启等操作。

## 十一、任务异常信息或proxy和agent的日志里包含有：不支持插件类型，pluginName: {插件的英名名}（错误码：13002）
- 问题原因      
  - proxy或agent的插件目录不存在该插件，如果插件列表中存在对应的插件，那可能在升级或迁移代理过程被遗留没保存下来，或者被其它方式误删了
  - 插件加载失败
  - 插件是内置插件或是内部功能插件，proxy和agent版本过低，未包含该插件

- 解决方法   
  - 重装安装该插件
  - 如果确认插件已安装，参考错误码：13005方案处理
  - proxy和agent版本过低的情况：
    - 如果是内置插件可以尝试安装该插件解决，否则需要升级版本。
    - 如果是内部功能插件则只能通过升级版本解决。

## 十二、数据库不支持、缺jdbc驱动、jdbc驱动版本过低等与驱动相关问题解决
无论什么原因需要改动jdbc驱动包的，请反馈给相关技术人员，技术人员会根据情况和需要将驱动包整合到安装包里面，以减少后期升级带来的麻烦。
- 0.3.0版本及之后的处理方式   
  安装包自带的驱动包保存在：`plugin.d/internal/snc-ng-agent-jdbc-drivers/libs`，改动前请确认是否已存在相应的驱动包（不区分版本号）
  - 添加jdbc驱动包   
    如果确认驱动包不存在，新建目录`plugin.d/jdbc-driver-libs`，将驱动jar包下到该目录重启服务即可。   
    该方式添加的驱动包不受服务升级、重装影响。
  - 替换jdbc驱动包   
    对于已存在的驱动包需要升级或降级，只能做替换处理，需要先删除存在的驱动jar包，再按上面的《添加jdbc驱动包》步骤处理。  
    注意：如果服务升级或重装，自带的驱动包会恢复原样，需要再次手动删除。
     
- 0.3.0版本之前的处理方式   
  找到对应插件的安装目录，直接在libs下替换或添加驱动jar包。   
  注意：内置插件会在服务升级或重装时恢复原样，需要再次手动处理。插件的升级或重装也一样会恢复原样需要再次手动处理。

### 当前支持数据库类型：
- Mysql
- Oracle
- SqlServer
- postgresql
- gbase
- DB2
- informix
- HANA
- 达梦dameng
- GaussDB  使用mysql驱动
- gbase
- GoldenDB 使用pgsql驱动
- OceanBase 使用mysql驱动
- OpenGuass
- mariadb 使用mysql驱动
- KingbaseES(人大金仓) 使用pgsql驱动
如果备注了使用指定数据库驱动，即数据库连接字符串需要使用该数据库驱动的写法，如指定使用mysql驱动，则用mysql的写法：jdbc:mysql://xxx:3306/db_name

## 十三、proxy或agent已启动，但服务还是离线状态（错误码：13008）
### proxy已启动但服务无法注册或还是离线状态
查看proxy的日志输出，服务启动正常会输出下面日志：
```text
KafkaConnector - kafka启动，assigned partitions: 0,1,2
```
proxy 如果已经输出上面日志，并无其它错误日志，表示proxy已经正常工作。   
**如果有出现该日志的排查方向**   
- 检查snc-ng-server和snc-ng-proxy的主机时间与kafka主机时间是否一致，如果差太多会导致消息被丢弃不处理
- 先查看proxy日志是否有可疑的错误信息，如果有根据错误信息进一步排查和处理。
- 将日志级别调成`DEBUG`，观察几分钟，查看日志是否有输出`定时上报状态`，如果有输出进入下一步排查，如果没有就跳到最后一步联系相关技术人员。
- 查看snc-ng-server的日志里面是否有proxy上报信息的日志，可根据proxy的ip进行日志搜索查看。
  - 如果有搜索proxy的上报日志，查看日志里面是还有错误日志，再根据相关错误日志进行排查和处理。
- 如果snc-ng-server日志里未查找到相关日志，则查看`snc-manager-up`这个topic里面是否有proxy的上报信息。
  - 如果topic里有搜索到proxy的上报信息，进一步确认该topic是否能正常消费数据，特别是使用消费者`snc-ng-server`进行确认。
    - 注意：proxy与kafka和snc-ng-server的服务器时间是否有同步，如果想着太多，会影响数据消费，导致snc-ng-server不能及时处理消息。
  - 如果topic里未搜索到proxy的上报信息，进一步确认该topic是否能发送数据。
- 上面几点经排查后未发现问题或发现问题无法解决，请联系相关技术人员处理。发现问题的，请记录下问题的排查记录。

**如果未出现该日志的排查方向**
- 查看proxy日志是否有错误日志，根据错误信息进一步排查处理。
- 查看proxy日志是否一直在输出`消息上报通道不可用，无法上报信息，服务不可用`，注意服务刚启动数秒内输出该日志是正常现象。
  - 查看kafka配置相关配置是否正确。
  - 查看kafka服务是否正常，特别是检查proxy配置的topic是否能正常消费数据。
  - proxy所属的集群是否启动了多个proxy，检查集群配置的topic的分区数，集群下的proxy个数不能超过分区数。
- 上面几点经排查后未发现问题或发现问题无法解决，请联系相关技术人员处理。发现问题的，请记录下问题的排查记录。

### agent已启动但服务无法注册或还是离线状态
查看agent的日志输出，服务启动正常会输出下面日志：
```text
agent connected to proxy[192.168.33.123:10031]
```
该日志的输出表示agent已经连接上proxy，如果agent连接的proxy集群有多个proxy也会输出多个对应proxy ip的日志，正常有多少个proxy就需要输出多少个日志。
但agent只要连接到其中一个就能正常工作，状态也应该要显示在线。   

**如果有出现该日志的排查方向**
- 先查看agent日志是否有可疑的错误信息，如果有根据错误信息进一步排查和处理。
- 确认agent所连接的proxy是否正常在线。
- 将日志级别调成`DEBUG`，观察几分钟，查看日志是否有输出`定时上报状态`，如果有输出进入下一步排查，如果没有就跳到最后一步联系相关技术人员。
- 将proxy日志级别调成`DEBUG`，观察几分钟，查看日志是否有agent的上报信息`接收到一条来自192.168.22.52:56436的SncBaseMessage[***]消息`，如果有输出进入下一步排查，如果没有就跳到最后一步联系相关技术人员。
  - 如果proxy有多个，可在agent日志搜索关键字`proxy连接集群发生变化`最后一条，看agent最后发送数据的proxy是那个。
- 查看snc-ng-server的日志里面是否有agent上报信息的日志，可根据agent的ip进行日志搜索查看。
    - 如果有搜索agent的上报日志，查看日志里面是还有错误日志，再根据相关错误日志进行排查和处理。
- 如果snc-ng-server日志里未查找到相关日志，则查看`snc-manager-up`这个topic里面是否有agent的上报信息并记录下来然后进入最后一步。
- 上面几点经排查后未发现问题或发现问题无法解决，请联系相关技术人员处理。发现问题的，请记录下问题的排查记录。

**如果未出现该日志的排查方向**
- 查看agent日志是否有错误日志，根据错误信息进一步排查处理。
- 查看agent日志是否一直在输出`消息上报通道不可用，无法上报信息，服务不可用`，注意服务刚启动数秒内输出该日志是正常现象。
    - 验证agent机器与proxy的端口是否能通信。
- 上面几点经排查后未发现问题或发现问题无法解决，请联系相关技术人员处理。发现问题的，请记录下问题的排查记录。

## 十四、日志一直输出“消息上报通道不可用，无法上报信息，服务不可用”（错误码：11001）
出现该日志的根本原因是服务无法与上级服务连接通信，注意：服务刚启动时因为还未与上级服务连通，可能会输出该日志，服务完全启动后就不再输出。
- 如果是agent服务，则表示agent与配置文件中的全部proxy无法连接：
  1. 检查配置文件中的proxy配置是否正确。
  2. 检查配置的proxy是否至少有一个在线并且服务正常。
  3. 确认本机与proxy机器的网络是否可达，可使用命令验证：`./jre/bin/java -jar snc-ng-agent-*.jar cmd portTest=ip:port`。
- 如果是proxy服务，则表示proxy无法消费配置文件中指定topic的数据：
  1. 确认kafka服务是否正常，相关配置是否确认。
  2. 检查proxy集群的proxy个数是否超过topic的分区数（kafka的特性，超过分区数的消费者无法消费数据）。
  3. 尝试指定消费组id为`snc-ng-consumer`（proxy的默认消费组）去消费topic数据，验证topic是否还正常。

## 十五、启动失败（错误码：13001）
如果服务无法启动或进程一会突然退出，如果出现该情况请先查看日志，根据日志的错误描述再进一步处理。

### 端口被占用
查看日志是否有出现`Address already in use: bind`或`端口已被占用`或`can not bind monitor port`，则表示服务需要用到的端口已被别的服务占用。涉及但不限于下面端口：
```properties
## proxy 需要使用的端口
# agent管理通信端口，必需使用
proxy.listen.port=10031
# 监控监听端口，开启监控功能时使用
proxy.monitor.zabbix.receivePort=10033

## agent 需要使用的端口
# 监控监听端口，开启监控功能时使用
agent.monitor.zabbix.receivePort=10032
```
如果是Windows系统报这种错，需要进一步排查系统的随机端口范围是否包含了需要使用的端口   
cmd查询命令：`netsh interface ipv4 show dynamicport tcp`   
- Start Port 表示随机开始端口
- Number of Ports 表示随机端口个数
即范围是从`Start Port`到`Start Port` + `Number of Ports`，这个范围的端口无法使用，需要修改端口配置在范围以外，或按下面方式修改系统配置：   
修改随机端口范围为原来Windows默认范围：`netsh interface ipv4 set dynamicport tcp start=49152 num=16384`，执行命令后需要重启系统生效。


### proxy日志输出“netty服务启动失败”、“netty start listening failed”
出现该日志的根本原因是proxy无法监听指定端口（由配置`proxy.listen.port`设置，默认10031）。   

### 无法启动并且无日志输出
尝试使用java命令直接启动jar包：./jre/bin/java -jar snc-ng-xxx*.jar

- 如果是aix7.1版本系统，请确认系统级别是否是`7100-03`及以上，官方要求该级别及以上的才支持jdk8，低于该级别无法运行。
  - 查看级别命令：`oslevel -r`
  - 官方说明：https://www.ibm.com/support/pages/java-sdk-aix
  - 解决方法：只能升级系统
  - 也发现有部分`7100-00`级别的系统能运行，根本原因未确认，可能跟`libc++`版本有关，查询命令`lslpp -L |grep xlC`，   
    查看`IBM XL C++ Runtime for AIX xxx`是否是6.1及以上版本，如果低于该版本可尝试升级看看，如何升级未展开研究，请自行研究如何升级和确认。

### 启动失败并在安装目录下输出了“core.xxxx”或“hs_err_pidxxx.log”
- 查看日志是否有关键字`C  [libresolv.so.2+0x7a91]  __libc_res_nquery+0x1c1`
   修复启动脚本，增加jvm启动参数：`-Djava.net.preferIPv4Stack=true`
- 上面未找到处理方法，联系技术人员处理

### Windows系统启动失败并报错：

## 十六、监控脚本错误（错误码：10001）
监控采集的脚本配置文件默认保存在以下目录，并且按下面目录顺序读取：
1. `config/monitor/sync` 从监控中心同步下来的采集脚本
2. `config/monitor` 自定义采集脚本（现在一般不用这种方式）
3. `plugin.d/internal/snc-ng-agent-monitor-server/monitor` 内置的采集脚本

- 脚本采集出现该错误码   
按上面说的目录顺序查看 `script` 目录是否存在对应的脚本文件
- jdbc采集出现该错误码   
按上面说的目录顺序查看 `jdbc/sql.properties` 文件是否配置了对应的监控项key
- snmp采集出现该错误码   
按上面说的目录顺序查看 `snmp/mib.yml` 文件是否配置了对应的监控项key

- 解决方案：
  - 脚本不存在：
    - 到`监控中心`-`配置管理`-`监控脚本`页面配置上对应的脚本，然后等待同步生效。
    - `监控脚本`管理里面已存在对应脚本配置：
      - 确认脚本配置是否确定，可通过该地址下载最终生成的脚本文件确认：http://{ip}:8080/snc-ng-server/monitorScript/download?checkUpdate=true
      - 如果确认最终生成的脚本没问题，可能是监控脚本未同步成功，根据下面《监控脚本未同步排查指导》章节处理。
  - 如果确认脚本已存在，联系相关技术人员处理。

### 监控脚本未同步排查指导
1. 确认`snc-ng-server`服务开启了监控脚本同步功能，检查是否存在下面配置。
   ```properties
   # 是否禁用监控脚本同步功能
   shsnc.monitor.script.sync.disable=false
   ```
2. 确认proxy或agent的配置是否开启了监控功能
   ```properties
   # proxy开启监控功能的配置
   proxy.monitor.zabbix.enable=true
   
   # agent开启监控功能的配置
   agent.monitor.zabbix.enable=true
   ```
3. 监控脚本同步逻辑，可用命令查看监控同步时间：unzip -z monitor_script.zip
   1. snc-ng-server定时从snc-amp服务同步脚本数据并保存在monitor目录下。需要脚本有修改才会触发同步。
   2. snc-ng-proxy定时上报同步脚本消息给snc-ng-server，如果有脚本有更新，snc-ng-server会下发更新脚本命令给proxy，proxy会从指定地址下载脚本到本地config/monitor目录下。
   3. snc-ng-agent定时上报同步脚本消息给snc-ng-server，如果有脚本有更新，snc-ng-server会下发更新脚本命令给agent，agent会通过proxy从指定地址下载脚本到本地config/monitor目录下。
   4. 脚本下载地址：http://192.168.1.1:10085/snc-ng-server/monitorScript/download 可手动尝试从该地址下载脚本。
4. 按下面顺序搜索服务的日志，搜索关键字“监控脚本”，查看是否有错误信息，根据信息提示处理。
   - snc-ng-agent -> snc-ng-proxy -> snc-ng-server
5. 联系相关技术人员

### 监控脚本采集结果与手动执行脚本的结果不一样。
1. 可执行以下测试命令验证结果：`java -jar snc-ng-proxy*.jar cmd 'metric=监控' host=proxyIp:monitorPort`
2. 参考第八点的《脚本执行结果与手动执行不一样》小节，然后执行测试命令做对比。

## 十七、kafka服务引起的错误（错误码：20001）
- 检查kafka服务是否正常。
- 检查引起错误的topic是否能发送数据或是否能消费数据。

## 十八、proxy向agent发消息失败（错误码：20002）
开启debug级别日志，直到问题复现后保留日志文件联系相关技术人员排查。

## 十九、agent向proxy发消息失败（错误码：20003）
开启debug级别日志，直到问题复现后保留日志文件联系相关技术人员排查。

## 二十、监控项key不支持或参数不正确（错误码：12001，12002）
12001：监控项key不支持   
12002：监控项key参数不正确   
可执行下面命令查看支持的监控项及参数说明：
```shell
./jre/bin/java -jar snc-ng-agent-*.jar cmd metricKeyDesc
```

## 二一、创建连接失败（错误码：12101，12102，12103）
12101：创建连接失败，按12102错误码方式处理   
12102：连接连续创建失败多次（即12101错误）被拉进了黑名单不再创建连接，直到黑名单失效（默认连续触发5次12101错误，5分钟后失效）   
- 确认目标服务是否正常运行。
- 确认连接配置是否正确，如ip、端口、用户和密码等，使用其它客户端工具验证连接配置是否可以可用。
- 确认本机与目标机器网络是否可达，可使用命令验证：`./jre/bin/java -jar snc-ng-agent-*.jar cmd portTest=ip:port`
12103：连接连续多次进入黑名单（即12102错误），被永久拉入黑名单，不会再创建连接，先按12102错误码方式处理，解决问题之后在页面对应的proxy或agent详情手动清理黑名单


## 二二、系统运行错误（错误码：00001）
如果出现该错误码表示系统可能运行不正常了，根据错误信息查找是否有下面关键字信息并根据指导做相应的处理，如果未找到对应描述则请联系技术人员处理。
- 关键字：java.lang.outofMemoryError: unable to create new native thread   
  线程创建失败，超过系统限制，可能原因：
   - 常驻任务过多。
   - 监控采集资源过多。
   - 自定义插件没控制线程的创建上限。
  使用下面命令确认问题。
   ```shell
   # 查看进程当前线程数
   ps -eLf |grep pid |grep -v grep |wc -l
   # 查看系统线程数限制
   ulimit -u
   ```
  解决方案：
    1. 修改系统`ulimit -u`的限制，建议最少设置65535，系统默认4096，一般是不够的。如何修改请自行搜索。
    2. 增加proxy或agent来分担压力。
    3. 监控采集资源过多的问题可以修改配置文件，将下面配置项适量改小，两项的值要设置成一样。
        ```properties
        agent.container.threadPools.monitor.corePoolSize=2
        agent.container.threadPools.monitor.maximumPoolSize=2
        ```
       
- 关键字：java.lang.outofMemoryError: Java heap space   
  内存溢出。
  解决方案：
    1. 增加采集服务来分担压力。
    2. 通过修改启动文件 snc_ng_server.sh 的启动参数，增加服务运行内存。


- 关键字： `打开的文件过多` 或 `Too many open files`  
  打开的文件句柄数超过了系统限制。
  使用下面命令确认问题。
   ```shell
   # 查看系统文件句柄数限制
   ulimit -n
   ```
  解决方案：
    1. 修改系统`ulimit -n`的限制或其它方式加大限制，建议最少设置10240。如何修改请自行搜索。
  注意：
    如果是agent出现该问题，问题不一定是出现在agent端，也可能是proxy端有问题，请连proxy端一起检查。


## 二三、插件运行错误（错误码：00002）
可能插件运行时的异常未处理，需要联系插件开发的相关技术人员处理


## 二四、代理突然离线，异常信息“长时间未上报心跳”（错误码：11000）
- 出现该问题主要原因是代理无法上报心跳，确认服务进程是否还在并查看日志是否有什么异常信息并根据异常信息提示处理。
- 查看代理安装目录下是否有类似`java_pidxxx.hprof`的文件，并且代理最后心跳时间与该文件的创建时间接近，那应该是内存溢出了，可尝试适当增加代理的运行内存。
- 进程不存在，尝试启动服务，如果服务启动失败，参考错误码：13001 方案处理。
- 进程存在，查看日志是否是错误码11001问题，否则参考错误码：13008 方案处理。 


## 二五、插件无法卸载成功（错误码：13003）
插件的卸载需要满足一定的条件才能支持，所以某些插件可能不支持卸载，这类插件需要重启proxy和agent服务完成卸载或重装。   
插件开发人员可以按插件开发文档的《插件热部署重装支持》章节开发插件以满足插件在线卸载功能。


## 二六、运行异常（错误码：20000）
出现该错误请到日志文件中找到对应的异常错误信息，一般错误信息有描述错误的原因，请根据错误原因做对应处理。如无法处理请保留错误日志，联系相关技术人员处理。


## 二七、任务重复下发（错误码：13004）
出现该错误是任务连续下发给proxy或agent，如果任务正常运行，该错误可忽略。如果该错误持续不断出现，则需要联系相关技术人员排查。


## 二八、业务异常（错误码：13000）
业务运行异常，用于提示，一般无需处理，请根据现场情况判断是否处理。


## 二九、执行任务解析失败（错误码：20004）
任务信息数据的json格式不正确，无法解析。
- 检查proxy或agent所属集群的topic是否有其它业务数据误发送过来
- 使用其它工具验证任务信息数据的json格式是否正确可解析。


## 三十、监控脚本加载失败（错误码：10002）
监控jdbc或snmp脚本配置有错误无法加载，请检查对应的脚本配置内容，脚本配置文件默认保存在以下目录，并且按下面目录顺序读取：
1. `config/monitor/sync` 从监控中心同步下来的采集脚本
2. `config/monitor` 自定义采集脚本（现在一般不用这种方式）
3. `plugin.d/internal/snc-ng-agent-monitor-server/monitor` 内置的采集脚本


## 三一、定时任务积压（错误码：13006）
当定时任务执行时间过长，但任务执行周期过短就出现该提示，如：任务周期为每分钟执行一次，但执行时间超了一分钟。      
如果偶尔出现又不影响业务可不处理，如果已经影响到业务了，需要调整任务配置或参数避免上面所述情况。   
偶尔出现，可在配置中添加以下面配置设置默认处理策略：
```properties
# 1.立即执行，不管理上次调度是否有执行完，2.添加到执行队列中，等上次调度执行完马上执行（会累计），3.放弃本次执行（默认3）
# agent同样支持该配置，将前缀proxy改为agent即可
proxy.schedule.default.misfire=3
```


## 三二、插件冲突（错误码：13007）
proxy或agent的插件目录`plugin.d`下存在相同的插件，保存在不同的目录下。加载规则是最新打包的插件，即以打包时间为准，不以版本为准。
- 手动删除不需要的插件目录


## 三三、常驻任务插件无法停止（错误码：20005）
日志出输出“任务已停止10秒线程还未退出，尝试中断线程”，是插件的start方法未正确处理退出事件，一直在运行不退出。   
需要插件开发人员参考插件开发文档的《常驻任务插件开发》章节正确处理退出事件。


## 三四、线程池队列已满（错误码：10003）
日志输出：pool[xxx] queue is full(size:1000), discarded task   
或任务报错：线程池[xxx]队列已经满[size:1000]，无法处理任务  
如果遇到上述错误表示任务太多，一下子无法处理完，可以尝试下面配置解决，其中`xxx`为线程池名称：
```
# 以下配置agent同样支持，将前缀proxy改为agent即可
# 队列大小，需要比上面的日志输出size值大
proxy.container.threadPools.xxx.queueSize=10000
# 任务处理线程数，默认5
proxy.container.threadPools.xxx.corePoolSize=5
proxy.container.threadPools.xxx.maximumPoolSize=5
```
如果是proxy修改配置后还无法解决，并且线程池是`dataSend`，则需要进一步判断是否是下面有多个agent同时返回太大量数据导致proxy处理不过来，如果是该种情况，则需要增加proxy来分担压力或将分配一分部agent给其它proxy集群。   

上述方法仍无法解决，需要联系相关技术人员进行进一步分析排查。


## 三五、proxy启动出现日志“kafka assigned partitions is empty”（错误码：10004）
- 情况一：proxy所属集群的proxy个数超出集群topic的分区数，超出的proxy无法会消费数据导致不能正常启动，解决方案如下：
  - 增加集群，将超过的proxy迁移到新的集群中。
  - 增加topic的分区数。
- 情况二：proxy所属集群的topic还有其它地方使用与proxy相同的消费组（默认：snc-ng-consumer）在消费数据，解决方案如下：
  - 找出这些消费数据的地方，修改其消费组与proxy的不一致。


## 三六、任务执行出现异常“java.lang.NoSuchMethodError”
- 情况一：插件使用了新版特性在该版本的proxy或agent上没有，根据错误信息报错的类和方法，对照插件开发文档的《插件版本兼容列表》章节确认是否是该问题，对应解决方案：
  - 升级proxy或agent到支持该特性的版本以上，最好升级到最新版本。
    - 同时插件开发人员按《插件版本兼容列表》章节的说明增加打包配置限制插件安装被到低版本的proxy或agent。
- 情况二：插件的依赖包冲突，根据错误信息找到报错类所属的依赖包，对比插件和proxy或agent是否存在相同的依赖包，解决方案：
  - 移除插件的依赖包，使用proxy或agent自带的依赖包。
  - 如果proxy或agent自带的依赖包版本过低，无法满足插件的功能，可尝试使用下面的方案临时解决并反馈回给技术人员在后续版本解决：
    1. proxy或agent下面配置禁用插件的隔离功能。
       ```properties
       # proxy配置
       proxy.container.pluginExcludeIsolation=plugin-english-name
       # agent配置
       agent.container.pluginExcludeIsolation=plugin-english-name
       ```
    2. 删除proxy或agent下的对应依赖包然后重启服务。


## 三七、WinRm执行失败相关问题（错误码：20007）
#### 执行出现异常错误：
- 异常信息包含以下其中一个内容：
  - `UndeclaredThrowableException: null`
  - `IOException: Authorization loop detected on Conduit "{http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd}WinRmPort.http-conduit" on URL "http://hostname:5985/wsman" with realm "null"`
  - `Could not send Message.`
- 问题原因：
  - 原因一：目标机器未开启WinRm服务功能。
  - 原因二：目标机器的认证限制远程访问执行脚本。
- 解决方法：
  1. 确认目标机器是否开启WinRm服务功能，查看服务是否启动命令：`winrm enumerate winrm/config/listener`。
     1. 开启WinRm服务：
        - https://learn.microsoft.com/zh-cn/windows/win32/winrm/installation-and-configuration-for-windows-remote-management
        - https://blog.csdn.net/u014108439/article/details/86706226
  2. 如果目标机器已经开启WinRm服务功能，执行下面命令开启远程访问权限：
     ```shell
      winrm set winrm/config/service/auth @{Basic="true"}
      winrm set winrm/config/service/auth @{CredSSP="true"}
      winrm set winrm/config/service/auth @{Certificate="true"}
      winrm set winrm/config/service @{AllowUnencrypted="true"}
     ```

#### 执行结果包含“系统中禁用执行脚本”
- 目标主机禁用了远程执行脚本功能，在目标主机执行下面命令开启远程脚本执行功能：
```shell
set-ExecutionPolicy RemoteSigned
```

## 三八、组[xxx]下无在线Proxy（错误码：13010）
- 先确认该集群组下是否安装了proxy并且至少有一个proxy在线。
    - 如果未安装proxy则安装proxy。或者将任务改成其它集群组的代理执行，再或者删除任务。
    - 如果已安装proxy但没有proxy在线，将proxy服务拉起即可。
- 该集群组下安装了proxy并且proxy服务的进程在线，但页面显示离线，参考错误码：13008方案处理。
- 该集群组下安装了proxy并且proxy服务显示在线：
  出现这种情况主要原因是proxy无法消费集群组topic的数据。
    - 在kafka服务的安装目录执行下面命令，查看是否有proxy在消费集群组topic的数据：
      ```shell
      ./kafka-consumer-groups.sh --bootstrap-server 127.0.0.1:9092 --group snc-ng-consumer --describe
      ```
    - 查看proxy启动时的日志：
        - 修改proxy日志级别为DEUBG并启动proxy服务。
        - 搜索日志关键字`KafkaConnector`过滤出proxy消费topic的日志，查看是否有启动消费或有报错，再做进一步处理。


## 三九、本地shell类型识别失败，aix系统执行本地脚本失败（错误码：10005）
1. 修改日志级别为DEBUG级别，然后重启服务，查看日志是否有`ExitCode: 127`的日志输出。
   如果有该日志输出，即服务使用的jre文件未授权可执行权限。
   在安装目录下执行命令`chmod -R +x jre`进行授权，然后重启服务。
2. 脚本里面不能指定使用`#!/bin/bash`，aix不支持bash。可以指定`#!/bin/sh`或`#!/bin/ksh`
3. 执行下面命令，并将结果反馈给相关技术人员
  - bash -c "echo snc-ng-agent-shell-check"
  - sh -c "echo snc-ng-agent-shell-check"
  - ksh -c "echo snc-ng-agent-shell-check"


## 四十、proxy的http请求转发下载超大文件或并发下载大文件失败
修改proxy的启动脚本snc_ng_server.sh，找到并修改启动参数`-XX:MaxDirectMemorySize=`并加大参数值


## 四一、非正常停止程序（错误码：10006）
没有使用自带的脚本命令`snc_ng_server.sh stop`来停止程序，而是使用了其它方式退出程序如：`kill pid`或`kill -9 pid`，   
又或者是因为主机关机或重启导致程序退出。   
如果需要停止程序请使用上面自带的脚本命令自己，或在页面上停止。


## 四二、消息回送失败（错误码：20008）
出现这个错误是agent无法发送消息给proxy，一般有以下几个情况：
- 无可用的proxy服务
  出现该错误提示表示agent无法连接到所有proxy，排查方式：
  1. 检查agent配置文件中的proxy是否正确。
  2. 检查所有proxy服务是否在线并且正常运行，如果在线，查看proxy的日志是否有错误。或者通过其它方式确认proxy是否正常。
  3. 检查agent主机与所有proxy的主机网络是否连通。

- 所有连接的proxy服务不可用
  出现该错误提示表示proxy服务是在运行的，但无法接收消息，一般是proxy接收数据流量达到上限，解决方案：
  1. 修改proxy的启动脚本snc_ng_server.sh，找到并修改启动参数`-XX:MaxDirectMemorySize=`并加大参数值。
  2. 如果集群下部署了多个agent，给proxy集群增加更多的proxy来分压。

- 目标proxy[xxx]未连接上
  出现该错误提示表示agent无法连接上指定的proxy，排查方式：
  1. 检查该proxy服务是否在线并且正常运行，如果在线，查看proxy的日志是否有错误。或者通过其它方式确认proxy是否正常。
  2. 检查agent主机与该proxy的主机网络是否连通。

- 目标proxy[xxx]服务不可用
  出现该错误提示表示该proxy服务是在运行的，但无法接收消息，一般是proxy接收数据流量达到上限，解决方案：
  1. 修改proxy的启动脚本snc_ng_server.sh，找到并修改启动参数`-XX:MaxDirectMemorySize=`并加大参数值。

## 四三、虚拟VIP等使用非主机本地网卡的安装部署
根据需要改对应的服务
- proxy安装添加或修改以下配置
   ```properties
   # 虚拟ip或指定ip，该ip会用来管理proxy，对proxy进行升级、启停操作，需要开通snc-ng-server的访问权限
   proxy.ip=192.168.1.10
   # 禁用本地网卡ip检测
   proxy.ignore.check.ip=true
   # 监听IP，用来管理agent，需要开通snc-ng-agent的访问权限
   proxy.listen.ip=10.10.1.27
   ```
- agent安装添加或修改以下配置
   ```properties
   # 虚拟ip或指定ip，该ip会用来管理agent，对agent进行升级、启停操作，需要开通snc-ng-proxy的访问权限
   agent.ip=192.168.1.10
   # 禁用本地网卡ip检测
   agent.ignore.check.ip=true
   ```

## 四四、proxy有多个网卡，与snc-ng-server和snc-ng-agent使用不同的网段通信   
proxy安装添加或修改以下配置
```properties
# 该ip会用来管理proxy，对proxy进行升级、启停操作，需要开通snc-ng-server的访问权限
proxy.ip=192.168.1.10
# 禁用本地网卡ip检测
proxy.ignore.check.ip=true
# 监听IP，用来管理agent，需要开通snc-ng-agent的访问权限
proxy.listen.ip=10.10.1.27
```


## 四五、消息回送失败（错误码：10007）
1. 非法连接，请确认proxy端和agent端都开启了ssl安全通信，查看配置文件：
```properties
# proxy端是否已经加了该配置
proxy.netty.ssl.enable=true

# agent端是否已经加了该配置
agent.netty.ssl.enable=true
```
2. 是否有修改过ssl相关配置，如：证书密码和证书文件。如有修改，请确认证书配置是否确认，证书文件是否可用


## 四六、监控脚本下载失败（错误码：11002）
出现该错误时，高于0.10.5版本的代理会在错误里面一起输出监控脚本的下载地址，低于该版本可以在错误日志前后找一下看有没有输出下载地址，如果未找到，
一般默认为snc-ng-server服务的地址：http://{snc-ng-server-IP}:10085/snc-ng-server/monitorScript/download

拿到下载地址后用别的工具尝试下载监控脚本，如curl命令，确保下载地址可以在代理的机器上可以正常下载:
- proxy下载失败的，直接在proxy的机器尝试用工具访问下载地址来下载监控脚本。
- agent下载失败的，因为agent一般是不让直连snc-ng-server服务，需要通过proxy来下载，所以需要尝试proxy集群的每一个proxy都去下载监控脚本，要确认全部proxy能正常下载监控脚本。
- 如果已经排除掉不是网络策略问题导致下载失败的，请根据《监控脚本未同步排查指导》节点进行进一步的排查。

如果网络策略问题导致snc-ng-proxy无法通过下载地址下载监控脚本，可以修改snc-ng-server的以下两个配置之一指定proxy的可下载地址：
```properties
## 注意以下配置是两选一，修改其中一个即可

# （优先修改该配置）snc-ng-proxy访问snc-ng-server服务的地址，用于解决proxy无法直连snc-ng-server的10085端口
snc.server.server-url=http://192.168.1.100:8080/snc-ng-server
# 当前上面配置不能修改或无法解决时，可以使用该配置。配置作用是配置监控脚本的完整下载地址，该地址要确保proxy能下载监控脚本
shsnc.monitor.scriptDownloadUrl=
```


## 四七、Windows使用指定用户启动agent
`bin/conf/wrapper.conf`直接以下配置：
```properties
wrapper.ntservice.account=username
wrapper.ntservice.password=password
```
官方配置说明：https://wrapper.tanukisoftware.com/doc/english/prop-ntservice-account.html


## 四八、非正常停止程序（错误码：10008）
系统时间有被修改。系统时间修改会导致任务运行错乱，所以程序停止运行，阻止任务运行导致数据错乱。如果设置了相关自保护功能，程序会自动启动，如果未设置自保护功能或长时间未启动，则需要人工启动程序。

## 四九、监控端口被非法访问（错误码：10009）
输出以下其中错误日志或信息：
- zabbix[x.x.x.x] is not allowed to access
- the ip x.x.x.x is not allowed to access
agent的监控端口默认只能接收zabbix主机发过来的数据，其它主机连接该端口都会被拒绝，该问题主机涉及到下面两个配置：
```properties
# 注意：下面配置的xxx表示是proxy或agent
# 监控端口，用来接收zabbix服务的数据
xxx.monitor.zabbix.receivePort=10032
# zabbix服务的ip，默认只有这个ip才能往监控端口发送数据，其它ip会被拒绝访问
xxx.monitor.zabbix.serverIp=192.168.2.100
```
解决方法：
先确认报错信息中的zabbix ip是否没错
  - 如果确认报错信息中的zabbix ip不是配置上zabbix主机会使用到的ip，请检查采集资源配置的zabbix是否正确。
  - zabbix主机有多个ip，使用了其它ip连接agent或proxy，或者是如NAT等网络环境配置导致了proxy或agent接收到的ip不是配置文件的ip，
    总之如果确认zabbix ip是没问题的，可以增加下面配置解决：
    ```properties
    # 监控端口接收数据的IP白名单，xxx需要改成对应的proxy或agent，值设置为all时表示接收所有ip请求
    xxx.monitor.zabbix.receiveAllowIps=192.168.2.100
    ```

## 四九、监控端口被非法访问（错误码：10009）
输出以下其中错误日志或信息：
- zabbix[x.x.x.x] is not allowed to access
- the ip x.x.x.x is not allowed to access
agent的监控端口默认只能接收zabbix主机发过来的数据，其它主机连接该端口都会被拒绝，该问题主机涉及到下面两个配置：
```properties
# 注意：下面配置的xxx表示是proxy或agent
# 监控端口，用来接收zabbix服务的数据
xxx.monitor.zabbix.receivePort=10032
# zabbix服务的ip，默认只有这个ip才能往监控端口发送数据，其它ip会被拒绝访问
xxx.monitor.zabbix.serverIp=192.168.2.100
```
解决方法：
先确认报错信息中的zabbix ip是否没错
  - 如果确认报错信息中的zabbix ip不是配置上zabbix主机会使用到的ip，请检查采集资源配置的zabbix是否正确。
  - zabbix主机有多个ip，使用了其它ip连接agent或proxy，或者是如NAT等网络环境配置导致了proxy或agent接收到的ip不是配置文件的ip，
    总之如果确认zabbix ip是没问题的，可以增加下面配置解决：
    ```properties
    # 监控端口接收数据的IP白名单，xxx需要改成对应的proxy或agent，值设置为all时表示接收所有ip请求
    xxx.monitor.zabbix.receiveAllowIps=192.168.2.100
    ```

## 五十、下发消息给agent失败（错误码：11003，11004）
proxy集群中部分proxy无法与报错的ip主机上的agent通信，导致无法下发消息，按下面方式进行逐步排查：
1. 确认agent主机与proxy集群中的全部proxy主机网络连通。
2. 确认agent与全部proxy是正常连接的，在agent的详情面的“链接情况”功能可以查看。
3. 如以上都确认没问题，请找出报该错误的proxy里面的日志出来，联系相关技术人员进行进一步排查。


## 五一、agent进程运行资源说明
- agent实际运行内存比分配的内存要高很多
如：修改agent的内存大小为64M，但实际采集到的内存大小数据可能为150多M，原因如下：
java程序的内存分成两部分，一部分是堆内内存，这个是可控的，可以自行调整；还有一部分是堆外内存，jvm会根据不同的系统和主机性能，一般额外再占到100M到200M内存，这部分是不可控的，可能会更多。

  
## 五二、不支持的监控项key（错误码：10010）
- 报错内容：unsupported metric key: xxx.xxx   
其中`xxx.xxx`为监控项key，出现该提示表示该监控项key不支持采集。排查方式：
1. 如果是AMP监控采集功能报了该错误，
   - 请先确认监控项key是用proxy或agent采集还是zabbix那边采集，并且检查监控项配置的采集方式，只有`Snc agent`、`Zabbix agent`和`Zabbix agent(active)`三种方式是通过proxy或agent采集的，其它都是在zabbix那边处理。
   - 如果确认监控项key写法和采集方式都没错，参考下面第2点排查。
2. 不管是不是AMP监控采集功能报了该错误，先用该命令查询确认当前版本的proxy或agent所支持的监控项key：java -jar snc-ng-proxy*.jar cmd metricKeyDesc excludeParam
   - 根据命令输出的监控项说明检查`xxx.xxx`是否有对应的key，并且写法是否是正确的。
   - 如果未找到对应的监控项说明，确认proxy或agent是否有新版本并且支持该key。
  

## 五三、网络不通
- 报错内容里面有出现：`Connection refused (Connection refused)` 或是 `拒绝访问`
出现该错误提示表示对端服务器端口无法访问，下面是提供的一些排查思路但不限于下面的排查方式，根因是端口无法访问，请根据实际的网络环境进行排查
1. 确认服务正常运行并且端口是启用的。
2. 检查防火墙配置是否有放通网络。
3. 使用如`telnet`之类的工具测试网络是否能连通。
4. 也可以使用proxy和agent自身提供的端口连通测试工具：`./jre/bin/java -jar snc-ng-agent-*.jar cmd portTest=ip:port`


## 五四、Windows计数器采集问题（错误码：13011）
- 报错内容里面有出现：`exit code: xxx`
    xxx为错误码，请根据微软官网的错误码表进出初步排查：https://learn.microsoft.com/zh-cn/windows/win32/perfctrs/pdh-error-codes
- 没有错误码的联系技术支持协助排查


## 五五、守护进程关联的proxy与对应agent的不一致（错误码：10011）
该问题是守护进程实际连接的proxy集群与agent实际连接的proxy集群不致导致的，一般是agent实际连接的proxy集群与agent配置文件上的不一致，如：用户手动修改了proxy配置，但没有重启agent。
请登录到agent主机检查以下几点（注意：一定要登录到主机检查）：
   1. 检查Agent配置文件的proxy是否与页面上关联的proxy集群一致。
   2. 检查守护进程配置文件里面的agent安装路径是否与Agent详情上的路径一致。

修复配置文件或确认配置无误重启守护进程和Agent解决。   
如果无法登录主机，尝试以下操作解决：
   1. 先尝试重启Agent看能不能解决。
   2. 如果重启Agent无法解决，尝试重新升级守护解决。




# 监控采集常见问题
proxy和agent的采集功能完全相同，区别点一般是proxy对接zabbix_server，agent对接zabbix_proxy，下面问题同时适用于proxy和agent排查，zabbix_server和zabbix_proxy也统称为`zabbix`。

## proxy和agent的监控采集问题初步定位和判断该联系谁处理和支持
正常一般情况下proxy和agent是接收到zabbix发过来的《发送设备名》监控项之后才会去采集数据，并在采集到数据之后会立即发送回zabbix，
在这期间出现的采集问题属于proxy和agent自身采集的问题，可以先联系中台组的相关支持技术人员协助，此外情况请先监控组的相关支持技术人员协助。   
判断依据可根据实际采集的代理的日志进行判断，按下面步骤查询日志是否存在下面日志内容：
1. 搜索关键字`agent.activehost[hostname]`，hostname为实际采集名称，如果不存在该日志，表示zabbix未发送设备名给proxy或agent，请先检查资源采集配置是否正确，或先联系监控组的相关支持技术人员协助排查。
2. 如果第1点日志存在，搜索采集名称，可以查该资源的相关采集日志，再进一步搜索监控项key，可以搜索指定监控项的采集日志，查看日志是否有异常错误信息，如果有就联系中台组的相关支持技术人员协助。
3. 搜索采集名称和关键字`send data to zabbix is success`，如果存在该日志，表示proxy或agent已经采集完成，并且已经将数据发送给zabbix，请先检查zabbix端服务是否有问题，然后先联系监控组的相关支持技术人员协助排查。



## 一、监控采集问题排查步骤指导

正常采集情况下按监控资源采集名称搜索运行日志会搜到下面日志内容，如搜索采集名称`linux_192.168.33.152`：
```text
1. receive zabbix message: agent.activehost[linux_192.168.33.152]
2. sync metric config from zabbix：[linux_192.168.33.152]
3. monitor_linux_192.168.33.152_snc.script20 - 添加到定时任务列表, 下次调度: 0220 172728
4. monitor_linux_192.168.33.152_snc.script20 - execute monitor collect: snc.script.cmd.ProTotal["cmd","ss -antu|grep ^tcp|wc -l"]
5. monitor_linux_192.168.33.152_snc.script20 - execute monitor collect result: 23
6. monitor_linux_192.168.33.152_snc.script20 - add to zabbix message queue, size: 1
7. monitor_linux_192.168.33.152_snc.script21 - 添加到定时任务列表, 下次调度: 0220 172728
8. monitor_linux_192.168.33.152_snc.script21 - execute monitor collect: snc.script.cmd.ProTotal["cmd","vmstat 1 2|tail -1|awk '{print $2}'"]
9. monitor_linux_192.168.33.152_snc.script21 - execute monitor collect result: 0
10. monitor_linux_192.168.33.152_snc.script21 - add to zabbix message queue, size: 1
11. send data to zabbix is success:true, host and size:{"linux_192.168.33.152":2}
```
#### 根据上面日志输出情况分析agent的采集状态。

##### 一、第1行日志：agent.activehost[xxx]
第1行是agent接收zabbix通知被告知需要采集的监控资源名称。   
如果没有接收该通知，主要原因是zabbix没给agent发送通知，属于外部原因，应该从外部开始排查。   
排查方向：
- agent配置文件的监控配置是否正确。
- agent的监控端口是否能访问，zabbix是否能与agent监控端口连接。
- 监控平台上的监控资源配置是否正确：
    - 监控资源的监控模式下的采集配是否正确，主要检查是agent的ip和端口是否无误。
    - 监控资源的监控模板是否有配置“发送设备名”监控项，并且采集方式为“Zabbix agent”模式和处于启用状态。

##### 二、第2行日志：同步监控配置
第2行根据监控资源名称向zabbix同步监控项配置。   
这一步是agent向zabbix发起请求获取监控设备的监控项配置   
如果没有输出该日志的排查方向：
- 确认是否有接收到第一行日志。
- 查看运行日志是否什么错误日志，可以使用该命令模拟这一步：./jre/bin/java -jar snc-ng-agent-*.jar cmd 'metric=agent.host.getItems[资源采集名称]'
    - 根据错误分析具体原因并解决。

##### 三、第3~10行日志：监控项采集记录
第3~6和7~10行是分别是两个监控项采集调度过程，以3~6行这个监控项采集为例。   
第3行是监控项到时触发执行采集，并生成下一次采集任务。   
第4行是监控项开始执行采集。   
第5行是监控项采集执行结果并打印采集结果。   
第6行是监控项将采集结果放到待发送队列。   
日志中的`monitor_linux_192.168.33.152_snc.script20`其中linux_192.168.33.152为资源采集名称，snc.script20为特定的监控项，第一次采集根据key生成。   
可以用后面部分`linux_192.168.33.152_snc.script20`搜索特定监控项的全部采集记录和过程。   
如果INFO级别日志只出现这4行日志表示agent在正常采集，请根据下面第9行的结果进行进一步排查。   
如果这4行日志采集过程中有错误日志，则表示可能采集失败（注意出现错误并不表示就一定是采集失败，有些监控项虽然报错了，但也有对应的采集结果返回）   
采集失败排查步骤：
1. 从第4行日志后面获取到监控项key。
2. 确认监控项key是否正确、参数顺序是否没错，可以根据手册上面的监控项key格式对比，或者执行命令查看当前版本支持的监控项：./jre/bin/java -jar snc-ng-agent-*.jar cmd metricKeyDesc。
3. 如果key的参数有宏变量，查看资源的监控配置里面的宏参数值是否无误。
4. 在agent同一个机器上使用其它工具验证参数是正确无误的，并确认agent的机子是可以正常访问被采集资源的服务。
5. 上面几步确认无误后，将key里面的宏参数替换成真正的值，然后用测试命令验证：./jre/bin/java -jar snc-ng-agent-*.jar cmd 'metric=监控项key'。
6. 查看运行日志找到错误日志，自己初步分析下看能否找到原因。
7. 对比下面章节的常见错误，查看是否有相同或类似的问题和解决方案。
8. 如果以上步骤未能解决问题，记录下初步排查结果，找相关负责人安排技术人员进行进一步排查，并把初步排查结果结论发送技术人员以便分析和快速定位问题。

##### 四、第11行日志：发送采集结果给zabbix
- 出现这一行日志并且success值为true，表示agent已经完成采集并将结果发送给zabbix，如果采集结果无法显示，问题不在agent这端，请从zabbix端开始往后排查。   
- 如果success值为false，也表示agent已将结果发送到zabbix端了，但zabbix处理数据失败，请从zabbix端开始排查。
- 如果未输出该行日志，而输出“发送采集数据到zabbix失败”，查看具体的错误信息，一般是zabbix无法连接，确认agent当前是否能与zabbix的端口通信。


## 二、采集出现错误日志

如果在下面没找到错误描述，请先到baidu或google等搜索引擎搜索一轮，一般都能找到错误的原因。

- can't find file name [xxx.xx]   
  无法找到监控脚本文件，到config/monitor目录下确认是否有相关的脚本。

- jdbc.xxxx cannot find in jdbc sql.properties config   
  jdbc采集的监控项key在sql.properties配置文件中未找到对应的key和sql语句。

- in the mib.yml not contains discovery item   
  snmp自发现采集在mib.yml中未找到对应key的配置

- java.lang.outofMemoryError: unable to create new native thread   
  线程创建失败，确认是否监控设备过多，单个设备默认分配5个线程，查看是否超过系统限制
   ```shell
   # 查看进程当前线程数
   ps -eLf |grep pid |grep -v grep |wc -l
   # 查看系统线程数限制
   ulimit -u
   ```
  解决方案：
    1. 增加采集服务proxy或agent来分担压力（推荐）。
    2. 修改配置文件，将下面配置项适量改小，两项的值要设置成一样。
   ```properties
   #主动模式线程池最小线程数[默认值：5]
   proxy.container.threadPools.monitor.corePoolSize=5
   #主动模式 线程池最大线程数[默认值：5]
   proxy.container.threadPools.monitor.maximumPoolSize=5
   ```

- java.lang.outofMemoryError: Java heap space   
  内存溢出，出现该错误可能是采集监控项太多，确认当前采集监控项总数，proxy不超过10W个监控项，agent不超过6k个监控项。

  解决方案：
    1. 增加采集服务来分担压力（推荐）。
    2. snc-ng-agent通过修改启动文件 snc_ng_server.sh 的启动参数，增加服务运行内存。

- java.lang.ArrayIndexOutOfBoundsException: n   
  n为一个数字，监控项key缺少必填参数。

## 三、proxy或agent不采集

1. 检查配置是否开启监控功能。
2. 确认zabbix服务是否正常，并且proxy或agent与对应的zabbix_server或zabbix_proxy能正常连通。
3. 检查日志是否有输出 `agent.activehost[xxx]`，表示接收到需要采集的资源xxx，如果无该日志，请确认资源监控配置是否正确和zabbix端服务是否正常。
4. 使用`agent.host.getItems[hostname]`key测试是否能同步到这些监控项，如果同步不到，表示zabbix端无监控配置，请确认zabbix端是否正常和资源监控配置是否正确。
   1. 先检查配置文件的zabbix与页面上资源监控配置的zabbix是否是一致。
   2. 如果排查页面的资源监控配置没问题，则需要检查zabbix端是否正常，请先自行初步排查，如查看zabbix日志等。zabbix端问题如果需要协助可联系监控组的同事帮忙排查。
5. 如果第3、4步正常，请根据第一节《监控采集问题排查步骤指导》进行进一步排查。


## 四、部分监控项不采集

1. 使用`agent.host.getItems`key测试是否能同步到这些监控项。
2. 如果未同步到监控项，查询监控配置是否正确。
3. 如果能同步到监控项，web端查看监控项是否有错误信息。
4. 根据第一节《监控采集问题排查步骤指导》第三点进行排查。

## 五、断采

1. 查看日志，断采的监控项断采时是否有采集错误，或是否采集结果为空。
2. 开启DEBUG或TRACE日志，收集断采时的日志。
3. 根据第一节《监控采集问题排查步骤指导》第三点的方式过滤出该监控项的所有采集调试日志进行分析。

## 六、服务无法连接或连接超时，IP和端口都无误，使用telnet命令能连通

- 应该是DNS解析问题
  - 修改目标主机的`/etc/hosts`文件，增加本机ip和主机名。   
    目前遇到过这问题的设备类型：`jmx`、`weblogic`和`oracle`
     ```text
     192.168.100.100  目标主机的hostname
     ```
  - 也可能是主机名冲突引起的DNS解析问题
    - 查看本机与目标服务器主机的hostname是否一样，如果一样则需要修改其中一个。
    - 查看本机的`/etc/hosts`是否存在目标服务器主机hostname的映射，并且ip不是目标主机，如果是，修改为目标主机ip。
  
- jmx服务解决方法：https://www.jianshu.com/p/b7790c9eabff   
   jmx服务的启动命令增加参数`-Djava.rmi.server.hostname=本机ip`绑定本机ip


## 七、proxy或agent的snmp协议无法采集到数据，但snmpwalk命令能获取数据

##### 1.普通监控项采集无数据
snmpwalk 命令是会扫描oid下面所有的子oid出来，如果刚好只有一个子oid，就会看起来像是获取到数据，实际获取的是子oid的数据。   
proxy或agent的snmp采集是类似snmpget命令方式获取数据，只能采集叶子oid的数据，不能采集父oid的数据。
理论上snmpget方式能获取到数据的，proxy或agent就能采集到数，要以snmpget方式为准。
##### 2.自发现监控项采集无数据
- 先确认配置是否正确，mib.yml里配置的oid与snmpwalk命令的一致
- 使用proxy或agent自带的snmp工具测试oid获取数据的情况：`./jar/bin/java -jar snc-ng-agent-*.jar cmd snmpTest help` 
- 浪潮或中兴的设备，尝试将mib.yml配置里的oid倒序写入：
  ```yaml
  # 原来配置方式
  snmp.discovery.Inspur:
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.1, name: diskIfIndex, alias: SNMPVALUE}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.2, name: diskIfCapacity}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.3, name: diskIfCF}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.4, name: diskIfCU}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.5, name: diskIfRS}
  ```
  ```yaml
  # 改成倒序配置
  snmp.discovery.Inspur:
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.5, name: diskIfRS}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.4, name: diskIfCU}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.3, name: diskIfCF}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.2, name: diskIfCapacity}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.1, name: diskIfIndex, alias: SNMPVALUE}
  ```
- 如果全部确认无误，尝试增加下面配置并把值调小：
  ```properties
  # 原本默认值50
  agent.snmp.maxNumRowsPerPDU=10
  # 原本默认值10
  agent.snmp.maxNumColumnsPerPDU=5
  ```
- 如果自发现采集的数据量很大，可尝试将自发现拆成多个自发现监采集，如果一次性采集数据量过大，有些snmp性能差的设备会处理不过来：
  ```yaml
  # 原来配置方式
  snmp.discovery.Inspur:
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.1, name: diskIfIndex, alias: SNMPVALUE}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.2, name: diskIfCapacity}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.3, name: diskIfCF}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.4, name: diskIfCU}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.5, name: diskIfRS}
  ```
  ```yaml
  # 修改为
  snmp.discovery.Inspur1:
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.1, name: diskIfIndex, alias: SNMPVALUE}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.2, name: diskIfCapacity}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.3, name: diskIfCF}
  snmp.discovery.Inspur2:
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.1, name: diskIfIndex, alias: SNMPVALUE}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.4, name: diskIfCU}
    - {oid: 1.3.6.1.4.1.25506.1.8.7.1.1.5, name: diskIfRS}
  ```

## 八、oracle数据库采集连接超过配置限制
当sql执行超时时，程序本地会关闭连接，但oracle数据库的机制不会马上关闭，直到sql执行结束才会释放连接。   
oracle官方说明：https://docs.oracle.com/en/database/oracle/oracle-database/21/jjdbc/JDBC-troubleshooting.html#GUID-E846B7AB-4032-473B-8E2F-E741FDD97012

- 从日志中找到执行超时的sql，尝试从sql上做优化解决。
  - 目前遇到下面sql会出现查询超过，在数据库无数据无其它连接时查询偶尔会出现查询几十秒的情况：   
    select count(*) as BCNT from v$lock where block=1

- 从oracle数据库端解决：
  1. 创建PROFILE :   
     SQL>create profile sess limit sessions_ per user 10; --最大连接数限制为20
  2. 将PROFILE指定给用户:   
     SQL>alter user SHSNC profile sess;

## 九、数据库连接失败，连接不上，无法连接
- 数据库连接失败最常见是连接参数不正确，请一定要先确认参数是否正确，包含账号、密码、IP、端口和连接串
- 确认proxy或agent本机与数据库网络是否能连通，可使用命令验证：`./jre/bin/java -jar snc-ng-agent-*.jar cmd portTest=ip:port`
- 确认数据库是否有白名单配置
- 使用proxy或agent自带的测试命令验证监控项key

### 数据库一些常见错误
- Oracle报错：ORA-12514, TNS:listener does not currently know of service requested in connect descriptor   
   确认连接参数是否正确，包含账号密码连接串，尤其是连接串，oracle的连接串有多种写法，请根据连接方式确认是否写正确，更多信息请网上搜索“jdbc oracle 连接串”
  - 方法一:使用service_name -> jdbc:oracle:thin:@//host:port/service_name     
    例如：jdbc:oracle:thin:@//192.168.1.1:1521/service_name
  - 方法二: 使用SID -> jdbc:oracle:thin:@host:port:SID   
    例如：jdbc:oracle:thin:@10.10.10.1:1521:orcl
  - 方法三：使用tnsname -> jdbc:oracle:thin:@TNSName   
    例如：jdbc:oracle:thin:@TNS_ALIAS_NAME
  
- Mysql报错关键字：Communications link failure   
  - 数据库无法连接，请先确认连接参数是否正确，尤其是账号、密码、IP和端口。
  - 如果是采集本机的数据库，连接地址用127.0.0.1和本机ip都试一下，有时候只能用127.0.0.1连，有时候只能用本机IP连。
  - 如果数据库版本是5.x的，可以尝试在url加上useSSL=false参数，如：jdbc:mysql://192.168.0.1:3306/db_name?useSSL=false

- SqlServer报错：“Encrypt”属性设置为“true”且“trustServerCertificate”属性设置为“false”
   或："encrypt" property is set to "true" and "trustServerCertificate" property is set to "false"
  - 在数据库的连接url后面加上参数`encrypt=false`或者`encrypt=true;trustServerCertificate=true`，如：
    - jdbc:sqlserver://localhost:1433;databaseName=TestDB;encrypt=false
    - jdbc:sqlserver://localhost:1433;databaseName=TestDB;encrypt=true;trustServerCertificate=true"
  - 如果修改url参数还是不行，参考下面地址的方法一，修改jre的文件`java.secrity`
    - https://blog.csdn.net/m0_61869253/article/details/136505805

- SqlServer报错：The server selected protocol version TLS10 is not accepted by client preferences [TLS13, TLS12]   
  - 修改代理自带jre文件`jre\lib\security\java.security`下面内容：
    - 找到配置`jdk.tls.disabledAlgorithms`，然后去掉 `TLSv1` `TLSv1.1` 两个配置，然后重启proxy服务即可。
    - 如果去掉上面说的配置之后还不行，可以再尝试去掉 `3DES_EDE_CBC` 之后再试。
  - 注意，修改是代理自带的jre文件，如果代理不是用自带jre启动服务的，就修改系统jdk对应的jre文件。


## 十、Redis采集常见问题
- 报错信息：NOAUTH Authentication required.
   Redis服务设置了连接认证，需要设置用户名和密码或只设置密码，如：`api.redis.info.xxx[ip,port,shsnc:shsnc123456]`
  - 如何验证Redis是否设置了连接认证：
    - 使用telnet命令连接到redis的端口，使用输入`PING`，返回`PONG`表示未设置；返回`NOAUTH Authentication required.`表示有设置。


## 十一、脚本采集密码参数会在执行命令明文显示解决方案
proxy和agent从以下版本开始支持下面方案隐藏命令行参数执行脚本
- 0.10.20及以上
- 0.11.7及以上
- 0.12.1及之后所有版本


- 方案一，通过环境变量给脚本参数，推荐使用，该方案兼容性强：    
    使用方式，监控项key需要包含`env`关键字，可通过脚本名的前缀或后缀加入该关键字，如：`envScriptName.sh`或`script_name_env.sh`   
    加入关键字之后参数将改为从环境变量传入，取参需要从环境变量获取，变量名为`SNC_PARAM1`，其中1为参数下标。   
    如key：script.envScriptName.sh[script,envScriptName.sh,value1,value2,value3]   
    脚本取参：
    ```shell
    echo "param1=$SNC_PARAM1"  # $SNC_PARAM1为第一个参数，值为value1
    echo "param2=$SNC_PARAM2"  # $SNC_PARAM2为第一个参数，值为value3
    echo "param3=$SNC_PARAM3"  # $SNC_PARAM2为第一个参数，值为value3
    ```

- 方案二，程序通过exec方式执行脚本，不显示脚本的执行命令，只支持linux下的shell脚本和python脚本：    
    使用方式，监控项key需要包含`hide`关键字，可通过脚本名的前缀或后缀加入该关键字，如：`hideScriptName.sh`或`script_name_hide.sh`   
    加入关键字之后脚本的执行方式改为用exec方式执行，该方式执行脚本通过ps无法查看脚本的执行参数。   
    如key：script.hiddenScriptName.sh[script,hiddenScriptName.sh,value1,value2,value3]   

- 方案三，通过配置全局开启方案二的方式，即脚本名称无需包含`hide`关键字默认以exec方式执行，开启后跟方案二执行逻辑一样：    
    proxy或agent添加配置：`<proxy|agent>.monitor.script.executeHidden=true` 


# 运维操作功能常见问题，适用于排查自动化运维操作和CMDB自发现任务等问题
运维操作功能都会由发起方先生成一个操作任务，该任务会指定一个全局唯一任务ID再下发给proxy或agent执行，所以可以根据该任务ID查询日志进行问题点定位。
## 一、初步定位问题
1、任务ID查询
任务ID都是由发起方生成的（即功能的开发方，如自动化运维和CMDB），如果在下面方式中未能找到任务ID，请联系功能开发者咨询如何获取到对应的任务ID。
- 自动化运维的任务ID查询
  - 自动化运维有很多功能都会生成运维操作，一般都会在日志里面输出任务ID，在执行对应功能之后自动化运维服务的日志中查找任务ID。
- CMDB自发现的任务ID查询
  1. 打开浏览器控制台（可按F12键打开）
  2. 进入执行日志详情页面，然后在控制台找到请求地址：/snc-cmdb-discovery/discovery/log/getExecuteLogPage
  3. 该地址返回该任务的全部执行记录，找到对应的需要排查执行记录数据，记录数据中的`ipLogId`和`scriptLogId`字段就是对应的任务ID了。

2、根据任务ID进行问题定位
运维操作任务执行流程如下，使用任务ID按下面流程搜索对应服务的日志进行初步定位问题点出现在哪个服务，再找到对应的服务负责人进行进一步的排查。
- 任务执行对象是snc-ng-proxy的流程：
    发起方 -> snc-ng-server -> kafka(下发topic) -> snc-ng-proxy -> kafka（返回topic） -> 发起方
- 任务执行对象是snc-ng-agent的流程：
    发起方 -> snc-ng-server -> kafka(下发topic) -> snc-ng-proxy -> snc-ng-agent -> snc-ng-proxy -> kafka（返回topic） -> 发起方
- 执行流程的节点搜索日志说明
  - 发起方：即功能所属的服务，根据功能查询到对应的任务ID。
  - snc-ng-server：接收任务并根据任务支持对象将任务下发到proxy或agent执行，如果INFO级别未搜索到任务ID相关日志，可尝试开启DEBUG级别日志之后再重试和搜索日志。
  - kafka(下发topic)：找到任务执行对象所属的proxy集群，集群topic为下发topic，或者查集群下任意proxy的配置里面的topic也可以，根据任务ID搜索该topic可以获取任务参数。
  - snc-ng-proxy：
    - 执行对象为proxy时，直接查对应proxy日志。
    - 执行对象为agent时，则需要查proxy集群下所有proxy的日志，并且查是否有下发给agent的日志和返回topic数据的日志。
  - snc-ng-agent：执行对象为agent时，直接查对应agent日志。
  - kafka（返回topic）：
    - 自动化运维一般是`dcp_realTime_result`。
    - CMDB自发现任务是`cmdb_dcp_realTime_result`。
    - 如果不是这两个topic，可以在下发topic里面找到的任务参数里面查topic关键字看具体是哪个topic。
- 根据上面的流程找出问题点，再找出问题服务的负责人做进一步的分析和排查。


## 十 插件问题
- simple-check 使用ping 的时候,网络能够正常ping 通,但是通过插件的ping 功能 返回失败.
    - 程序必须使用 root 运行,发送和接收原始套接字（raw sockets） 例如  ICMP,需要root 权限.
    - 否则需要通过root 执行 一下命令  setcap cap_net_raw+ep /home/shsnc/jre/bin/java (程序启动的jre程序路径)





