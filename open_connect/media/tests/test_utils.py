"""Test media utilities"""
# pylint: disable=invalid-name
from subprocess import check_output
from unittest import skipIf

from django.test import TestCase
from mock import patch, Mock

from open_connect.media import utils


def gifsicle_not_installed():
    """Return True if Gifsicle is not installed"""
    try:
        version_output = check_output(['gifsicle', '--version'])
        if 'Gifsicle' in version_output:
            return False
        else:
            return True
    except OSError:
        return True


@skipIf(gifsicle_not_installed(), 'Gifsicle Not Installed')
class TestResizeGif(TestCase):
    """Test the resize_gif utility"""
    def setUp(self):
        """Setup TestResizeGif"""
        pipe_patcher = patch('open_connect.media.utils.PIPE')
        self.mock_pipe = pipe_patcher.start()
        self.addCleanup(pipe_patcher.stop)

        pil_patcher = patch('open_connect.media.utils.PILImage')
        self.mock_pil = pil_patcher.start()
        mock_pil_response = Mock()
        mock_pil_response.format = 'GIF'
        self.mock_pil.open.return_value = mock_pil_response
        self.addCleanup(pil_patcher.stop)

    @patch('open_connect.media.utils.Popen')
    def test_gifsicle(self, mock_popen):
        """Test a valid call to gifsicle"""
        mock_image = Mock()
        mock_process = Mock()
        mock_process.communicate.return_value = ('hey', False)
        mock_popen.return_value = mock_process
        result, error = utils.resize_gif(mock_image, (300, 300))
        mock_popen.assert_called_once_with(
            [
                'gifsicle',
                '--resize-fit',
                '300x300'
            ],
            stdin=self.mock_pipe, stdout=self.mock_pipe
        )
        self.assertEqual(mock_image.seek.call_count, 3)
        mock_process.communicate.assert_called_once_with(
            mock_image.read())

        self.assertEqual(result, 'hey')
        self.assertEqual(error, False)

    @patch('open_connect.media.utils.Popen')
    def test_gifsicle_empty_result(self, mock_popen):
        """Test a call to gifsicle that has an empty result"""
        mock_image = Mock()
        mock_process = Mock()
        mock_process.communicate.return_value = ('', False)
        mock_popen.return_value = mock_process
        result, error = utils.resize_gif(mock_image, (300, 300))
        mock_popen.assert_called_once_with(
            [
                'gifsicle',
                '--resize-fit',
                '300x300'
            ],
            stdin=self.mock_pipe, stdout=self.mock_pipe
        )
        self.assertEqual(mock_image.seek.call_count, 3)
        mock_process.communicate.assert_called_once_with(
            mock_image.read())

        self.assertEqual(result, '')
        self.assertEqual(error, True)

    @patch('open_connect.media.utils.Popen')
    def test_gifsicle_throws_error(self, mock_popen):
        """Test gifsicle where Gifsicle throws an error"""
        mock_image = Mock()
        mock_popen.side_effect = OSError('Misc Exception')
        result, error = utils.resize_gif(mock_image, (300, 300))
        mock_popen.assert_called_once()
        self.assertEqual(result, '')
        self.assertEqual(error, True)

    @patch('open_connect.media.utils.PILImage')
    def test_gifsicle_only_allows_gif(self, mock_pil):
        """Test gifsicle where something other than a GIF is thrown in"""
        # Here a Mock() object will be passed in, which is obviously not 'GIF'
        with self.assertRaises(ValueError):
            utils.resize_gif(Mock(), (300, 300))
