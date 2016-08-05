# -*- mode: python -*-

block_cipher = None


a = Analysis(['scraper.py', 'wdstart.py', 'sendEmail.py', 'copyProfile.py'],
             pathex=['F:\\Users\\mlmn\\Downloads\\FBGroupScraper\\Delivery2\\Delivery\\FBGroupScraper-Source'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='scraper',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='scraper')
