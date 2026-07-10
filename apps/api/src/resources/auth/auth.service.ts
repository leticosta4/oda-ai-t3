import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class AuthService {
  constructor(private readonly jwtService: JwtService) {}

  async login(body: any) {
    if (body.username === 'admin' && body.password === 'admin123') {
      const payload = { username: body.username, sub: 'admin-id' };
      // return {
      //   access_token: this.jwtService.sign(payload),
      // };
    }
    throw new UnauthorizedException('Credenciais inválidas');
  }
}
