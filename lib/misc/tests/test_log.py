import dictconfig
import logging
import sys
import json

from django.conf import settings

from mock import Mock, patch
from nose.tools import eq_
from metlog.config import client_from_dict_config

import amo.tests
import commonware.log
from lib.log_settings_base import error_fmt
from lib.log_settings_base import get_sentry_handler
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


class TestMetlogStdLibLogging(amo.tests.TestCase):

    def setUp(self):
        METLOG_CONF = {
            'sender': {
                'class': 'metlog.senders.logging.StdLibLoggingSender',
                'logger_name': 'z.metlog',
                }
            }
        self.metlog = client_from_dict_config(METLOG_CONF)
        self.logger = logging.getLogger('z.metlog')

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
        self.metlog.error(msg)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(logrecord.msg, msg)
        self.assertEqual(logrecord.levelname, 'ERROR')

        msg = 'info'
        self.metlog.info(msg)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(logrecord.msg, msg)
        self.assertEqual(logrecord.levelname, 'INFO')

        msg = 'warn'
        self.metlog.warn(msg)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(logrecord.msg, msg)
        self.assertEqual(logrecord.levelname, 'WARNING')

        # debug shouldn't log
        msg = 'debug'
        self.metlog.debug(msg)
        logrecord = self.handler.buffer[-1]
        self.assertNotEqual(logrecord.msg, msg)
        self.assertNotEqual(logrecord.levelname, 'DEBUG')

    def test_other_sends_json(self):
        timer = 'footimer'
        elapsed = 4
        self.metlog.timer_send(timer, elapsed)
        logrecord = self.handler.buffer[-1]
        self.assertEqual(logrecord.levelname, 'INFO')
        msg = json.loads(logrecord.msg)
        self.assertEqual(msg['type'], 'timer')
        self.assertEqual(msg['payload'], str(elapsed))
        self.assertEqual(msg['fields']['name'], timer)


class TestRaven(amo.tests.TestCase):
    def setUp(self):
        """
        We need to set the settings.METLOG instance to use a
        DebugCaptureSender so that we can inspect the sent messages.
        """

        metlog = settings.METLOG
        METLOG_CONF = {
            'logger': 'zamboni',
            'sender': {'class': 'metlog.senders.DebugCaptureSender'},
        }
        from metlog.config import client_from_dict_config
        self.metlog = client_from_dict_config(METLOG_CONF, metlog)

    def test_send_raven(self):
        try:
            1 / 0
        except:
            self.metlog.raven('blah')

        eq_(len(self.metlog.sender.msgs), 1)
        msg = json.loads(self.metlog.sender.msgs[0])
        eq_(msg['type'], 'sentry')


class TestStdTastypieHandler(amo.tests.TestCase):
    def setUp(self):
        """
        The SentryHandler had it's constructor arguments change.
        This just verifies that client wrapped inside the
        SentryHandler is properly initialized

        When logging.config.dictConfig is used to configure logging
        with a 'one-shot' config dictionary, any previously
        instantiated singleton loggers (ie: all old loggers not in
        the new config) will be explicitly disabled.
        """
        self.logger = logging.getLogger('django.request.tastypie')
        self.logger.disabled = False

        self._orig_handlers = self.logger.handlers
        while self.logger.handlers:
            self.logger.removeHandler(self.logger.handlers[0])
        self._handler = get_sentry_handler()
        def capture_func(record):
            self._captured = record
        self._handler.emit = capture_func
        self.logger.addHandler(self._handler)

    def tearDown(self):
        while self.logger.handlers:
            self.logger.removeHandler(self.logger.handlers[0])
        while self._orig_handlers:
            self.logger.addHandler(self._orig_handlers[0])

    def test_tastypie_handler(self):
        err_msg = "tastypie error triggered"
        try:
            1 / 0
        except:
            self.logger.error(err_msg)

        # This will fail if the SentryHandler isn't configured
        # properly
        assert self._handler.client.is_enabled()
        eq_("tastypie error triggered", self._captured.message)
