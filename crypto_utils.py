"""
암호화 유틸리티 모듈
Upbit Pro Algo-Trader v3.0

API 키 등 민감 정보의 안전한 암호화/복호화
"""

import os
import base64
import hashlib
from typing import Optional

# 암호화 라이브러리 (옵션)
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class CryptoManager:
    """암호화 관리 클래스"""
    
    # 솔트 파일 경로
    SALT_FILE = ".upbit_salt"
    
    def __init__(self, master_password: str = ""):
        self.master_password = master_password
        self.cipher: Optional[Fernet] = None
        self.is_initialized = False
        
        if master_password:
            self.initialize(master_password)
    
    def initialize(self, master_password: str) -> bool:
        """암호화 초기화"""
        if not CRYPTO_AVAILABLE:
            print("[암호화] cryptography 라이브러리가 설치되지 않았습니다.")
            return False
        
        try:
            self.master_password = master_password
            salt = self._get_or_create_salt()
            key = self._derive_key(master_password, salt)
            self.cipher = Fernet(key)
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"[암호화] 초기화 실패: {e}")
            self.is_initialized = False
            return False
    
    def _get_or_create_salt(self) -> bytes:
        """솔트 조회 또는 생성"""
        if os.path.exists(self.SALT_FILE):
            with open(self.SALT_FILE, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(self.SALT_FILE, 'wb') as f:
                f.write(salt)
            return salt
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """비밀번호에서 키 파생 (PBKDF2)"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """문자열 암호화"""
        if not self.is_initialized or not self.cipher:
            raise RuntimeError("암호화 모듈이 초기화되지 않았습니다.")
        
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """문자열 복호화"""
        if not self.is_initialized or not self.cipher:
            raise RuntimeError("암호화 모듈이 초기화되지 않았습니다.")
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except InvalidToken:
            raise ValueError("복호화 실패: 비밀번호가 올바르지 않습니다.")
    
    def verify_password(self, encrypted_test: str) -> bool:
        """비밀번호 검증 (테스트 문자열 복호화 시도)"""
        try:
            self.decrypt(encrypted_test)
            return True
        except (ValueError, Exception):
            return False
    
    def hash_password(self, password: str) -> str:
        """비밀번호 해시 생성 (저장용)"""
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            100000
        )
        return base64.b64encode(salt + pwd_hash).decode()
    
    def verify_password_hash(self, password: str, stored_hash: str) -> bool:
        """저장된 해시와 비밀번호 비교"""
        try:
            decoded = base64.b64decode(stored_hash.encode())
            salt = decoded[:16]
            stored_pwd_hash = decoded[16:]
            
            pwd_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt,
                100000
            )
            return pwd_hash == stored_pwd_hash
        except Exception:
            return False


class SecureStorage:
    """보안 저장소 - API 키 등 민감 정보 관리"""
    
    SECURE_FILE = ".upbit_secure"
    TEST_STRING = "UPBIT_SECURE_TEST"
    
    def __init__(self):
        self.crypto: Optional[CryptoManager] = None
        self.data = {}
        self.is_unlocked = False
    
    def is_first_run(self) -> bool:
        """첫 실행 여부 확인"""
        return not os.path.exists(self.SECURE_FILE)
    
    def setup(self, master_password: str) -> bool:
        """보안 저장소 초기 설정"""
        self.crypto = CryptoManager(master_password)
        if not self.crypto.is_initialized:
            return False
        
        # 테스트 문자열 암호화하여 저장 (비밀번호 검증용)
        self.data = {
            '_test': self.crypto.encrypt(self.TEST_STRING),
            'access_key': '',
            'secret_key': '',
            'telegram_token': '',
            'telegram_chat_id': ''
        }
        self._save()
        self.is_unlocked = True
        return True
    
    def unlock(self, master_password: str) -> bool:
        """저장소 잠금 해제"""
        self.crypto = CryptoManager(master_password)
        if not self.crypto.is_initialized:
            return False
        
        try:
            self._load()
            # 테스트 문자열로 비밀번호 검증
            test = self.crypto.decrypt(self.data.get('_test', ''))
            if test != self.TEST_STRING:
                return False
            self.is_unlocked = True
            return True
        except Exception:
            return False
    
    def _load(self):
        """파일에서 로드"""
        if os.path.exists(self.SECURE_FILE):
            import json
            with open(self.SECURE_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
    
    def _save(self):
        """파일에 저장"""
        import json
        with open(self.SECURE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def set_api_keys(self, access_key: str, secret_key: str):
        """API 키 암호화 저장"""
        if not self.is_unlocked:
            raise RuntimeError("저장소가 잠겨 있습니다.")
        
        self.data['access_key'] = self.crypto.encrypt(access_key) if access_key else ''
        self.data['secret_key'] = self.crypto.encrypt(secret_key) if secret_key else ''
        self._save()
    
    def get_api_keys(self) -> tuple:
        """API 키 복호화 조회"""
        if not self.is_unlocked:
            raise RuntimeError("저장소가 잠겨 있습니다.")
        
        access_key = ''
        secret_key = ''
        
        if self.data.get('access_key'):
            access_key = self.crypto.decrypt(self.data['access_key'])
        if self.data.get('secret_key'):
            secret_key = self.crypto.decrypt(self.data['secret_key'])
        
        return access_key, secret_key
    
    def set_telegram_config(self, token: str, chat_id: str):
        """텔레그램 설정 암호화 저장"""
        if not self.is_unlocked:
            raise RuntimeError("저장소가 잠겨 있습니다.")
        
        self.data['telegram_token'] = self.crypto.encrypt(token) if token else ''
        self.data['telegram_chat_id'] = self.crypto.encrypt(chat_id) if chat_id else ''
        self._save()
    
    def get_telegram_config(self) -> tuple:
        """텔레그램 설정 복호화 조회"""
        if not self.is_unlocked:
            return '', ''
        
        token = ''
        chat_id = ''
        
        try:
            if self.data.get('telegram_token'):
                token = self.crypto.decrypt(self.data['telegram_token'])
            if self.data.get('telegram_chat_id'):
                chat_id = self.crypto.decrypt(self.data['telegram_chat_id'])
        except Exception:
            pass
        
        return token, chat_id


# 싱글톤 인스턴스
_secure_storage: Optional[SecureStorage] = None

def get_secure_storage() -> SecureStorage:
    """보안 저장소 싱글톤 인스턴스 반환"""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage
