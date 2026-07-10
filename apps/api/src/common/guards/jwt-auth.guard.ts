import { ExecutionContext, Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    const request = context.switchToHttp().getRequest();
    const method = request.method;

    // Métodos de leitura são livres e públicos
    if (['GET', 'OPTIONS', 'HEAD'].includes(method)) {
      return true;
    }

    // Exige token para POST, PATCH, PUT, DELETE
    return super.canActivate(context);
  }
}
