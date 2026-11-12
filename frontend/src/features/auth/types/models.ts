export interface CurrentUser {
  id: number;
  username: string;
  email: string;
  fullName: string | null;
  isActive: boolean;
  isSuperuser: boolean;
}
