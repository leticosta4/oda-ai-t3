import { Injectable } from '@nestjs/common';
import { CreateLinhaPesquisaDto } from './dto/create-linha-pesquisa.dto';
import { UpdateLinhaPesquisaDto } from './dto/update-linha-pesquisa.dto';
import { PrismaService } from 'src/prisma/prisma.service';

@Injectable()
export class LinhaPesquisaService {
  constructor(private readonly prisma: PrismaService) {}
  create(createLinhaPesquisaDto: CreateLinhaPesquisaDto) {
    return 'This action adds a new linhaPesquisa';
  }

  findAll() {
    return this.prisma.linhaPesquisa.findMany({
      omit: {
        criadoEm: true,
        atualizadoEm: true,
      },
    });
  }

  findOne(id: number) {
    return `This action returns a #${id} linhaPesquisa`;
  }

  update(id: number, updateLinhaPesquisaDto: UpdateLinhaPesquisaDto) {
    return `This action updates a #${id} linhaPesquisa`;
  }

  remove(id: number) {
    return `This action removes a #${id} linhaPesquisa`;
  }
}
