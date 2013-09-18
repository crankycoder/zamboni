import dictconfig
import logging
import sys
import json

from django.conf import settings

from mock import Mock, patch
from nose.tools import eq_
from heka.config import client_from_dict_config

import amo.tests
import commonware.log
from lib.log_settings_base import error_fmt
from lib.misc.admin_log import ErrorTypeHandler
from test_utils import RequestFactory


cfg = {
    'version': 1,
    'formatters': {
        'error': {
            '()': commonware.log.Formatter,
            'datefmt': '%H:%M:%S',
            'format': ('%s: [%%(USERNAME)s][%%(REMOTE_ADDR)s] %s'
                       % (settings.SYSLOG_TAG, error_fmt)),
        },
    },
    'handlers': {
        'test_syslog': {
            'class': 'lib.misc.admin_log.ErrorSyslogHandler',
            'formatter': 'error',
        },
    },
    'loggers': {
        'test.lib.misc.logging': {
            'handlers': ['test_syslog'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}


class TestErrorLog(amo.tests.TestCase):

    def setUp(self):
        dictconfig.dictConfig(cfg)
        self.log = logging.getLogger('test.lib.misc.logging')
        self.request = RequestFactory().get('http://foo.com/blargh')

    def division_error(self):
        try:
            1 / 0
        except:
            return sys.exc_info()

    def io_error(self):
        class IOError(Exception):
            pass
        try:
            raise IOError('request data read error')
        except:
            return sys.exc_info()

    def fake_record(self, exc_info):
        record = Mock()
        record.exc_info = exc_info
        record.should_email = None
        return record

    def test_should_email(self):
        et = ErrorTypeHandler()
        assert et.should_email(self.fake_record(self.division_error()))

    def test_should_not_email(self):
        et = ErrorTypeHandler()
        assert not et.should_email(self.fake_record(self.io_error()))

    @patch('lib.misc.admin_log.ErrorTypeHandler.emitted')
    def test_called_email(self, emitted):
        self.log.error('blargh!',
                       exc_info=self.division_error(),
                       extra={'request': self.request})
        eq_(set([n[0][0] for n in emitted.call_args_list]),
            set(['errorsysloghandler']))

    @patch('lib.misc.admin_log.ErrorTypeHandler.emitted')
    def test_called_no_email(self, emitted):
        self.log.error('blargh!',
                       exc_info=self.io_error(),
                       extra={'request': self.request})
        eq_(set([n[0][0] for n in emitted.call_args_list]),
            set(['errorsysloghandler']))

    @patch('lib.misc.admin_log.ErrorTypeHandler.emitted')
    def test_no_exc_info_request(self, emitted):
        self.log.error('blargh!')
        eq_(set([n[0][0] for n in emitted.call_args_list]),
            set(['errorsysloghandler']))

    @patch('lib.misc.admin_log.ErrorTypeHandler.emitted')
    def test_no_request(self, emitted):
        self.log.error('blargh!',
                       exc_info=self.io_error())
        eq_(set([n[0][0] for n in emitted.call_args_list]),
            set(['errorsysloghandler']))


class TestHekaStdLibLogging(amo.tests.TestCase):

    """
    The StdLibLoggingStream is only used for *debugging* purposes.

    Some detail is lost when you write out to a StdLibLoggingStream -
    specifically the logging level.
    """

    def setUp(self):
        HEKA_CONF = {
            'encoder': 'heka.encoders.StdlibJSONEncoder',
            'stream': {
                'class': 'heka.streams.logging.StdLibLoggingStream',
                'logger_name': 'z.heka',
                }
            }
        self.heka = client_from_dict_config(HEKA_CONF)
        self.logger = logging.getLogger('z.heka')

        """
        When logging.config.dictConfig is used to configure logging
        with a 'one-shot' config dictionary, any previously
        instantiated singleton loggers (ie: all old loggers not in
        the new config) will be explicitly disabled.
        """
        self.logger.disabled = False

        self._orig_handlers = self.logger.handlers
        self.handler = logging.handlers.BufferingHandler(65536)
        self.logger.handlers = [self.handler]

    def tearDown(self):
        self.logger.handlers = self._orig_handlers

    def test_oldstyle_sends_msg(self):
        msg = 'error'
        self.heka.error(msg)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(json.loads(logrecord.msg)['payload'], msg)
        loglevel = [f for f in json.loads(logrecord.msg)['fields'] if f['name'] == 'loglevel'][0]
        self.assertEqual(loglevel['value_integer'][0], logging.ERROR)

        msg = 'info'
        self.heka.info(msg)
        logrecord = self.handler.buffer[-1]

        self.assertEqual(json.loads(logrecord.msg)['payload'], msg)
        self.assertEqual(logrecord.levelname, 'INFO')

        msg = 'warn'
        self.heka.warn(msg)
        logrecord = self.handler.buffer[-1]

        jdata = json.loads(logrecord.msg)
        self.assertEqual(jdata['payload'], msg)

        loglevel = [f for f in jdata['fields'] if f['name'] == 'loglevel'][0]
        self.assertEqual(loglevel['value_integer'], [logging.WARN])

        # debug shouldn't log
        msg = 'debug'
        self.heka.debug(msg)
        logrecord = self.handler.buffer[-1]

        jdata = json.loads(logrecord.msg)
        loglevel = [f for f in jdata['fields'] if f['name'] == 'loglevel'][0]
        self.assertNotEqual(jdata['payload'], msg)
        self.assertNotEqual(loglevel['value_integer'], [logging.DEBUG])

    def test_other_sends_json(self):
        timer = 'footimer'
        elapsed = 4
        self.heka.timer_send(timer, elapsed)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(logrecord.levelname, 'INFO')
        msg = json.loads(logrecord.msg)
        self.assertEqual(msg['type'], 'timer')
        self.assertEqual(msg['payload'], str(elapsed))

        name = [f for f in msg['fields'] if f['name'] == 'name'][0]
        self.assertEqual(name['value_string'], [timer])


class TestRaven(amo.tests.TestCase):
    def setUp(self):
        """
        We need to set the settings.HEKA instance to use a
        DebugCaptureStream so that we can inspect the sent messages.
        """

        heka = settings.HEKA
        HEKA_CONF = {
            'logger': 'zamboni',
            'stream': {'class': 'heka.streams.DebugCaptureStream'},
            'encoder': 'heka.encoders.NullEncoder'
        }
        from heka.config import client_from_dict_config
        self.heka = client_from_dict_config(HEKA_CONF, heka)

    def test_send_raven(self):
        try:
            1 / 0
        except:
            self.heka.raven('blah')

        eq_(len(self.heka.stream.msgs), 1)
        msg = self.heka.stream.msgs[0]
        eq_(msg.type, 'sentry')
