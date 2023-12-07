import os
import time
import json
import threading
import subprocess
from .important import *
from .log import log, log_replace

class psiphon(threading.Thread):
    def __init__(self, command, port, kuota_data_limit, multi_tunnel_enabled, verbose):
        super(psiphon, self).__init__()

        self.multi_tunnel_enabled = multi_tunnel_enabled
        self.kuota_data_limit = kuota_data_limit
        self.command = command
        self.verbose = verbose
        self.port = port

        self.tunnels = 32 if self.multi_tunnel_enabled else 1
        self.kuota_data = {}
        self.kuota_data_all = 0
        self.force_stop = False

        self.daemon = True

    def log(self, value, color='[G1]'):
        log(value, status=self.port, color=color)

    def log_replace(self, value, color='[G1]'):
        log_replace(value, color=color)

    def size(self, bytes, suffixes=['B', 'KB', 'MB', 'GB'], i=0):
        while bytes >= 1000 and i < len(suffixes) - 1:
            bytes /= 1000; i += 1

        return '{:.3f} {}'.format(bytes, suffixes[i])

    def check_kuota_data(self, id, sent, received):
        self.kuota_data[id] += sent + received
        self.kuota_data_all += sent + received

        for x in self.kuota_data:
            if self.kuota_data_limit > 0 and self.kuota_data[x] >= self.kuota_data_limit:
                if sent == 0 and received <= 20000:
                    return False

        return True

    def run(self):
        time.sleep(1.000)
        self.log('Connecting')
        time.sleep(1.500)
        if len(psiphon_stop) >= 1: return
        while True:
            try:
                self.connected = 0
                self.kuota_data = {}
                self.kuota_data_all = 0
                self.reconnecting_color = '[G1]'
                process = subprocess.Popen(self.command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                for line in process.stdout:
                    if len(psiphon_stop) >= 1:
                        self.force_stop = True
                        break
                    
                    line = json.loads(line.decode().strip() + '\r')
                    info = line['noticeType']

                    if info == 'BytesTransferred':
                        id, sent, received = line['data']['diagnosticID'], line['data']['sent'], line['data']['received']
                        if not self.check_kuota_data(id, sent, received):
                            break
                        ids = ''
                        for x in self.kuota_data:
                            ids += '({}) '.format(self.size(self.kuota_data[x]))
                        self.log_replace('{} {}'.format(self.port, ids))

                    elif info == 'ConnectingServer':
                        if self.verbose:
                            self.log(f"{line['data']['diagnosticID']}: {line['data']['region']} {line['data']['protocol']}")

                    elif info == 'ActiveTunnel':
                        self.connected += 1
                        self.kuota_data[line['data']['diagnosticID']] = 0
                        if self.verbose: 
                            self.log(f"{line['data']['protocol']}", color='[Y1]')
                        if self.connected == self.tunnels:
                            with lock:
                               proxies.append(['127.0.0.1', self.port])
                            self.log('Connected' + ' ' * 16, color='[Y1]')

                    elif info == 'Alert':
                        message = line['data']['message']

                        if 'SOCKS proxy accept error' in message:
                            self.log('SOCKS proxy accept error ({})'.format('connected' if self.connected else 'disconnected'), color='[R1]')

                        elif 'meek round trip failed' in message:
                            if self.connected == self.tunnels:
                                if message == 'meek round trip failed: remote error: tls: bad record MAC' or \
                                   message == 'meek round trip failed: context deadline exceeded' or \
                                   message == 'meek round trip failed: EOF' or \
                                   'psiphon.CustomTLSDial' in message:
                                    # ~
                                    self.reconnecting_color = '[R1]'
                                    break
                                else:
                                    self.log(f'001: \n\n{line}\n', color='[P1]')

                        elif 'A connection attempt failed because the connected party did not properly respond after a period of time' in message or \
                         'context canceled' in message or \
                         'API request rejected' in message or \
                         'RemoteAddr returns nil' in message or \
                         'network is unreachable' in message or \
                         'close tunnel ssh error' in message or \
                         'tactics request failed' in message or \
                         'unexpected status code:' in message or \
                         'meek connection is closed' in message or \
                         'psiphon.(*MeekConn).relay' in message or \
                         'meek connection has closed' in message or \
                         'response status: 403 Forbidden' in message or \
                         'making proxy request: unexpected EOF' in message or \
                         'tunnel.dialTunnel: dialConn is not a Closer' in message or \
                         'psiphon.(*ServerContext).DoConnectedRequest' in message or \
                         'No connection could be made because the target machine actively refused it.' in message or \
                         'no such host' in message:
                            continue

                        elif 'controller shutdown due to component failure' in message or \
                          'psiphon.(*ServerContext).DoStatusRequest' in message or \
                          'psiphon.(*Tunnel).sendSshKeepAlive' in message or \
                          'psiphon.(*MeekConn).readPayload' in message or \
                          'psiphon.(*Tunnel).Activate' in message or \
                          'underlying conn is closed' in message or \
                          'duplicate tunnel:' in message or \
                          'tunnel failed:' in message:
                            # ~
                            self.reconnecting_color = '[R1]'
                            break

                        elif 'controller shutdown due to component failure' in message or \
                          'No address associated with hostname' in message:
                            self.log(f"007:\n\n{line}\n", color='[R1]')
                            # self.reconnecting_color = '[R1]'
                            # break

                        else:
                            self.log(line, color='[R1]')

                    '''
                    elif info == 'AvailableEgressRegions' or \
                      info == 'UpstreamProxyError' or \
                      info == 'ClientRegion' or \
                      info == 'NetworkID' or \
                      info == 'Homepage' or \
                      info == 'Tunnels' or \
                      info == 'Exiting' or \
                      info == 'showUser' or \
                      info == 'BuildInfo' or \
                      info == 'SessionId' or \
                      info == 'LivenessTest' or \
                      info == 'ConnectedServer' or \
                      info == 'ServerTimestamp' or \
                      info == 'LocalProxyError' or \
                      info == 'CandidateServers' or \
                      info == 'ConnectingServer' or \
                      info == 'PruneServerEntry' or \
                      info == 'RequestedTactics' or \
                      info == 'RequestingTactics' or \
                      info == 'TotalBytesTransferred' or \
                      info == 'ClientUpgradeAvailable' or \
                      info == 'EstablishTunnelTimeout' or \
                      info == 'ActiveAuthorizationIDs' or \
                      info == 'ListeningSocksProxyPort' or \
                      info == 'Info':
                        continue
                    '''
            except json.decoder.JSONDecodeError:
                self.force_stop = True
                self.log(line.decode().strip(), color='[R1]')
                self.log('Another process is running!', color='[R1]')
            except KeyboardInterrupt:
                pass
            except Exception as exception:
                self.log('Exception: {}'.format(exception), color='[R1]')
            finally:
                if self.force_stop:
                    process.kill()
                    return
                with lock:
                    if ['127.0.0.1', self.port] in proxies:
                        proxies.remove(['127.0.0.1', self.port])
                try:
                    process.kill()
                    if self.connected:
                        self.connected = False
                    self.log('Reconnecting ({})'.format(self.size(self.kuota_data_all)), color=self.reconnecting_color)
                except Exception as exception:
                    self.log('Stopped', color='[R1]')
                    break
