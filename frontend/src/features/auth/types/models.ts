// input: 后端 auth 响应字段映射
// output: TokenPair / CurrentUser 类型
// owner: wanhua.gu
// pos: auth feature - 认证领域数据形状；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  fullName: string | null;
  isActive: boolean;
  isSuperuser: boolean;
}
