# `npm start` が `127.0.0.1:1234` だけで待ち受けているか確認する方法

作成日: 2026-05-17

## 結論

`npm start` 後に、本当に外部向けではなく `127.0.0.1:1234` だけで待ち受けているかは、OSの「LISTEN中のソケット」を確認すると判断できます。

見るべきポイントは次です。

- 安全側: `127.0.0.1:1234` だけが `LISTEN`
- 注意: `0.0.0.0:1234` が `LISTEN`
- 注意: `*:1234` が `LISTEN`
- 注意: `[::]:1234` が `LISTEN`

`127.0.0.1` は loopback address です。同じPC自身からの接続だけを受ける特別なアドレスなので、通常はLAN内や外部PCから直接アクセスできません。

一方、`0.0.0.0` や `*` は全ネットワークインターフェースで待ち受ける指定です。これが `1234` に出ている場合、ファイアウォールやネットワーク設定次第で外部PCからアクセスされ得ます。

## 事前確認: コード上の設定

現在の `gulpfile.js` は次の設定です。

```js
connect.server({
  host: '127.0.0.1',
  port: 1234,
  https: false,
});
```

これはコード上は `127.0.0.1` だけで待ち受ける設定です。ただし、最終確認は実際に `npm start` した後のOSソケット状態で行うのが確実です。

## Linux / WSL で確認する方法

`npm start` を起動したターミナルとは別のターミナルで実行します。

### より安全な方法: `npm start` 前後の差分を見る

より確実に確認するなら、`npm start` の前後で `ss -ltnp` の結果を保存し、増えた `1234` の待ち受けが `127.0.0.1` であることを確認します。

理由は、`npm start` 後だけを見ると、もともと別プロセスが `1234` を使っていた場合や、別の待ち受けと混同する可能性があるためです。前後差分を見ると、「`npm start` によって新しく増えた待ち受け」が分かります。

1. `npm start` の前に確認結果を保存します。

```bash
ss -ltnp > /tmp/before-npm-start-ports.txt
```

2. 別ターミナルで `npm start` を起動します。

```bash
npm start
```

3. 起動後にもう一度保存します。

```bash
ss -ltnp > /tmp/after-npm-start-ports.txt
```

4. 差分を確認します。

```bash
diff -u /tmp/before-npm-start-ports.txt /tmp/after-npm-start-ports.txt
```

安全側の差分例:

```diff
+LISTEN 0 511 127.0.0.1:1234 0.0.0.0:* users:(("node",pid=12345,fd=18))
```

この場合、`npm start` によって増えた待ち受けが `127.0.0.1:1234` なので、ローカルPC内向けです。

注意が必要な差分例:

```diff
+LISTEN 0 511 0.0.0.0:1234 0.0.0.0:* users:(("node",pid=12345,fd=18))
```

または:

```diff
+LISTEN 0 511 [::]:1234 [::]:* users:(("node",pid=12345,fd=18))
```

この場合、全インターフェース待ち受けの可能性があるため、外部PCからアクセスされるリスクがあります。

`diff` を使わずに `1234` だけ見る簡易版:

```bash
ss -ltnp | grep ':1234'
```

ここで `127.0.0.1:1234` だけが表示されることを確認します。

### 方法1: `ss`

```bash
ss -ltnp | grep ':1234'
```

安全側の例:

```text
LISTEN 0 511 127.0.0.1:1234 0.0.0.0:* users:(("node",pid=12345,fd=18))
```

注意が必要な例:

```text
LISTEN 0 511 0.0.0.0:1234 0.0.0.0:* users:(("node",pid=12345,fd=18))
```

または:

```text
LISTEN 0 511 [::]:1234 [::]:* users:(("node",pid=12345,fd=18))
```

### 方法2: `lsof`

```bash
lsof -iTCP:1234 -sTCP:LISTEN -n -P
```

安全側の例:

```text
COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node    12345 user   18u  IPv4  ...       0t0  TCP 127.0.0.1:1234 (LISTEN)
```

注意が必要な例:

```text
COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
node    12345 user   18u  IPv4  ...       0t0  TCP *:1234 (LISTEN)
```

## macOS で確認する方法

```bash
lsof -iTCP:1234 -sTCP:LISTEN -n -P
```

安全側:

```text
TCP 127.0.0.1:1234 (LISTEN)
```

注意:

```text
TCP *:1234 (LISTEN)
```

macOSの `*` は全インターフェース待ち受けを意味します。`127.0.0.1` だけならローカルPC内向けです。

## Windows PowerShell で確認する方法

Windows上で `npm start` している場合は、PowerShellで次を実行します。

```powershell
Get-NetTCPConnection -LocalPort 1234 -State Listen | Format-Table LocalAddress,LocalPort,OwningProcess
```

安全側の例:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
127.0.0.1         1234         12345
```

注意が必要な例:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
0.0.0.0           1234         12345
```

または:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
::                1234         12345
```

`0.0.0.0` や `::` は全インターフェース待ち受けの可能性があるため、`127.0.0.1` だけの場合よりリスクが高いです。

どのプロセスか確認したい場合:

```powershell
Get-Process -Id <OwningProcess>
```

## Windows での確認手順まとめ

Windowsで確認する場合は、まず PowerShell で `Get-NetTCPConnection` を使うのが分かりやすいです。

### 1. `npm start` を起動する

PowerShellまたはコマンドプロンプトで、リポジトリのディレクトリに移動して起動します。

```powershell
npm start
```

### 2. 別のPowerShellで `1234` の待ち受けを確認する

```powershell
Get-NetTCPConnection -LocalPort 1234 -State Listen | Format-Table LocalAddress,LocalPort,OwningProcess
```

安全側の例:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
127.0.0.1         1234         12345
```

この場合、`127.0.0.1:1234` だけで待ち受けています。`127.0.0.1` は自分自身だけを指す loopback address なので、通常は同じWindows PCからしかアクセスできません。

注意が必要な例:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
0.0.0.0           1234         12345
```

または:

```text
LocalAddress LocalPort OwningProcess
------------ --------- -------------
::                1234         12345
```

`0.0.0.0` や `::` は全ネットワークインターフェースで待ち受けている可能性があります。この場合、Windowsファイアウォールやネットワーク設定次第で、別PCから `http://<Windows PCのIPアドレス>:1234/` にアクセスできる可能性があります。

### 3. 待ち受けているプロセス名を確認する

`OwningProcess` に表示された数字を使います。

```powershell
Get-Process -Id 12345
```

`node` など、`npm start` に関係するプロセスであることを確認します。

### 4. `netstat` でも確認できる

PowerShellまたはコマンドプロンプトで実行します。

```powershell
netstat -ano | findstr ":1234"
```

安全側の例:

```text
TCP    127.0.0.1:1234    0.0.0.0:0    LISTENING    12345
```

注意が必要な例:

```text
TCP    0.0.0.0:1234      0.0.0.0:0    LISTENING    12345
```

### 5. WSLを使っている場合は Windows 側の portproxy も確認する

WSL内で `npm start` している場合、WSL内のサーバが `127.0.0.1` だけで待ち受けていても、Windows側の portproxy によって外部公開されることがあります。

Windows側の管理者PowerShellで確認します。

```powershell
netsh interface portproxy show all
```

注意が必要な例:

```text
Listen on ipv4:             Connect to ipv4:

Address         Port        Address         Port
--------------- ----------  --------------- ----------
0.0.0.0         1234        <WSLのIP>        1234
```

この設定がある場合、Windowsの `0.0.0.0:1234` に来た通信がWSL側の `1234` に転送される可能性があります。

安全側の条件:

- `Get-NetTCPConnection -LocalPort 1234 -State Listen` に `0.0.0.0:1234` や `:::1234` 相当の表示が出ない。
- `netsh interface portproxy show all` に `0.0.0.0 1234` 相当の設定がない。
- `netstat -ano | findstr ":1234"` でも `127.0.0.1:1234` だけが `LISTENING` している。

## Windows の `netstat` で確認する方法

PowerShellまたはコマンドプロンプトで実行します。

```powershell
netstat -ano | findstr ":1234"
```

安全側:

```text
TCP    127.0.0.1:1234    0.0.0.0:0    LISTENING    12345
```

注意:

```text
TCP    0.0.0.0:1234      0.0.0.0:0    LISTENING    12345
```

## WSLで `npm start` している場合の追加確認

WSL内で `npm start` している場合は、まずWSL側で確認します。

```bash
ss -ltnp | grep ':1234'
```

期待する状態:

```text
127.0.0.1:1234
```

ただし、WSLではWindows側の portproxy やファイアウォール設定で外部公開される可能性があります。Windows側の管理者PowerShellで次も確認します。

```powershell
netsh interface portproxy show all
```

注意が必要な例:

```text
Listen on ipv4:             Connect to ipv4:

Address         Port        Address         Port
--------------- ----------  --------------- ----------
0.0.0.0         1234        <WSLのIP>        1234
```

この設定があると、Windows側の `0.0.0.0:1234` に来た通信がWSLの `1234` へ転送される可能性があります。

安全側の見方:

- `netsh interface portproxy show all` に `0.0.0.0 1234` がない。
- Windows側でも `Get-NetTCPConnection -LocalPort 1234 -State Listen` に `0.0.0.0:1234` が出ない。

## なぜこの方法で確認できるのか

Webサーバは、ブラウザからの接続を受けるためにOSへ「このIPアドレスとポートで待ち受けます」と登録します。この状態を TCP の `LISTEN` と呼びます。

たとえば `npm start` の開発サーバが次のように待ち受けている場合:

```text
127.0.0.1:1234 LISTEN
```

これは「自分自身、つまり同じPCから `127.0.0.1:1234` に来た接続だけを受ける」という意味です。LAN内の別PCが `http://このPCのLAN IP:1234/` にアクセスしても、サーバはそのLAN IPでは待ち受けていないため、通常は届きません。

一方で次の場合:

```text
0.0.0.0:1234 LISTEN
```

これは「そのPCが持つ全IPv4インターフェースで `1234` を待ち受ける」という意味です。PCに `192.168.x.x` のLAN IPがある場合、ファイアウォールが許可していれば、別PCから `http://192.168.x.x:1234/` で到達できる可能性があります。

つまり、実際の `LISTEN` アドレスを見ることで、サーバがローカルPC内だけに閉じているのか、外部ネットワークにも開いている可能性があるのかを確認できます。

## 判定表

| 表示 | 判定 | 理由 |
| --- | --- | --- |
| `127.0.0.1:1234` | 安全側 | loopback のみ。通常は同じPCからだけ到達可能 |
| `localhost:1234` | ほぼ安全側 | 通常は `127.0.0.1` または `::1` を指す。ただし実表示はIPで確認する |
| `::1:1234` | 安全側 | IPv6 loopback のみ |
| `0.0.0.0:1234` | 注意 | 全IPv4インターフェース待ち受け |
| `*:1234` | 注意 | 全インターフェース待ち受けの表示 |
| `[::]:1234` / `:::1234` | 注意 | 全IPv6インターフェース待ち受け。環境によってIPv4も受ける場合がある |

## このリポジトリでの確認手順

1. `npm start` を起動する。

```bash
npm start
```

2. 別ターミナルで待ち受けを確認する。

Linux / WSL / macOS:

```bash
lsof -iTCP:1234 -sTCP:LISTEN -n -P
```

または Linux / WSL:

```bash
ss -ltnp | grep ':1234'
```

Windows PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 1234 -State Listen | Format-Table LocalAddress,LocalPort,OwningProcess
```

3. `127.0.0.1:1234` だけが `LISTEN` していることを確認する。

4. `0.0.0.0:1234`、`*:1234`、`[::]:1234` が出ていないことを確認する。

5. WSLの場合はWindows側で portproxy も確認する。

```powershell
netsh interface portproxy show all
```

6. `listenaddress=0.0.0.0` / `listenport=1234` 相当の設定がないことを確認する。

## まとめ用の短い説明

> `npm start` 後に `lsof`、`ss`、または Windows の `Get-NetTCPConnection` で `1234` の `LISTEN` アドレスを確認します。`127.0.0.1:1234` だけならサーバはloopbackにだけバインドされており、通常は同じPCからしかアクセスできません。`0.0.0.0:1234`、`*:1234`、`[::]:1234` が出ている場合は全インターフェース待ち受けの可能性があり、外部PCからアクセスされるリスクがあります。

より厳密には、`npm start` の前後で `ss -ltnp` の結果を保存して `diff` を取り、`npm start` によって新しく増えた `1234` の待ち受けが `127.0.0.1:1234` であることを確認します。これにより、既存の別プロセスと混同せずに確認できます。
