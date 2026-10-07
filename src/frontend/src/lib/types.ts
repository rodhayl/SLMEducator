export type Role = 'student' | 'teacher' | 'admin';
export interface User { id: number; username: string; role: Role; first_name: string; last_name: string; email: string; grade_level?: string | null }
