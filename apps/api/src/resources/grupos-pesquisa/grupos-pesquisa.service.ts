import { Injectable } from '@nestjs/common';
import { CreateGruposPesquisaDto } from './dto/create-grupos-pesquisa.dto';
import { UpdateGruposPesquisaDto } from './dto/update-grupos-pesquisa.dto';
import { PrismaService } from 'src/prisma/prisma.service';

@Injectable()
export class GruposPesquisaService {
  constructor(private readonly prisma: PrismaService) {}
  create(createGruposPesquisaDto: CreateGruposPesquisaDto) {
    return 'This action adds a new gruposPesquisa';
  }

  findAll() {
    return this.prisma.grupoPesquisa.findMany({
      omit: {
        criadoEm: true,
        atualizadoEm: true,
      },
    });
  }

  findOne(id: number) {
    return `This action returns a #${id} gruposPesquisa`;
  }

  update(id: number, updateGruposPesquisaDto: UpdateGruposPesquisaDto) {
    return `This action updates a #${id} gruposPesquisa`;
  }

  remove(id: number) {
    return `This action removes a #${id} gruposPesquisa`;
  }
}
